from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (Brand, BrandOutlet, Client, ClientUser, GoogleLocation, PlatformAccount, SwiggyOutlet,
                     ZomatoOutlet)


class MappingStatusFilter(admin.SimpleListFilter):
    title = "mapping"
    parameter_name = "mapped"

    def lookups(self, request, model_admin):
        return [("no", "Not mapped to a store"), ("yes", "Mapped")]

    def queryset(self, request, queryset):
        if self.value() == "no":
            return queryset.filter(brand_outlet__isnull=True)
        if self.value() == "yes":
            return queryset.filter(brand_outlet__isnull=False)
        return queryset


class OwnerFilter(admin.SimpleListFilter):
    title = "owner"
    parameter_name = "owned"

    def lookups(self, request, model_admin):
        return [("no", "No client yet"), ("yes", "Has a client")]

    def queryset(self, request, queryset):
        if self.value() == "no":
            return queryset.filter(client__isnull=True)
        if self.value() == "yes":
            return queryset.filter(client__isnull=False)
        return queryset


class AssignClientForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.filter(is_active=True))


class CatalogAdmin(admin.ModelAdmin):
    """Catalog rows come from the collector. Staff decide which client owns each id."""

    list_filter = [OwnerFilter, "client", MappingStatusFilter, "is_active", "account", "city"]
    readonly_fields = ["account", "first_seen_at", "last_seen_at"]
    list_per_page = 100
    actions = ["assign_to_client", "remove_client"]
    autocomplete_fields = ["client"]

    @admin.display(description="Mapped to")
    def mapped_to(self, obj):
        bo = getattr(obj, "brand_outlet", None)
        return f"{bo.brand} · {bo.outlet_name}" if bo else "—"

    @admin.action(description="Assign selected ids to a client…")
    def assign_to_client(self, request, queryset):
        if "apply" in request.POST:
            form = AssignClientForm(request.POST)
            if form.is_valid():
                client = form.cleaned_data["client"]
                # an id already used in another client's store can't change owner silently
                blocked = queryset.filter(brand_outlet__isnull=False).exclude(brand_outlet__brand__client=client)
                n_blocked = blocked.count()
                updated = queryset.exclude(pk__in=blocked.values("pk")).update(client=client)
                self.message_user(request, f"{updated} ids now belong to {client}.", messages.SUCCESS)
                if n_blocked:
                    self.message_user(request, f"{n_blocked} ids skipped: they are mapped to another client's store. "
                                               "Unmap them there first.", messages.WARNING)
                return None
        else:
            form = AssignClientForm()
        return render(request, "admin/outlets/assign_client.html", {
            **self.admin_site.each_context(request), "title": "Assign ids to a client", "form": form,
            "queryset": queryset, "opts": self.model._meta, "action_checkbox_name": ACTION_CHECKBOX_NAME,
        })

    @admin.action(description="Remove client from selected ids")
    def remove_client(self, request, queryset):
        mapped = queryset.filter(brand_outlet__isnull=False).count()
        updated = queryset.filter(brand_outlet__isnull=True).update(client=None)
        self.message_user(request, f"{updated} ids no longer belong to a client.", messages.SUCCESS)
        if mapped:
            self.message_user(request, f"{mapped} ids skipped: still mapped to a store.", messages.WARNING)

    def get_search_results(self, request, queryset, search_term):
        queryset, distinct = super().get_search_results(request, queryset, search_term)
        # Store pickers only offer active ids that have an owner and aren't mapped yet
        if request.GET.get("model_name") == "brandoutlet":
            queryset = queryset.filter(is_active=True, client__isnull=False, brand_outlet__isnull=True)
        return queryset, distinct

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("brand_outlet__brand", "account", "client")


@admin.register(ZomatoOutlet)
class ZomatoOutletAdmin(CatalogAdmin):
    list_display = ["res_id", "name", "area", "city", "client", "is_active", "mapped_to", "account"]
    search_fields = ["res_id", "name", "area", "city"]


@admin.register(SwiggyOutlet)
class SwiggyOutletAdmin(CatalogAdmin):
    list_display = ["swiggy_id", "name", "area", "city", "client", "is_active", "mapped_to", "account"]
    search_fields = ["swiggy_id", "name", "area", "city"]


@admin.register(GoogleLocation)
class GoogleLocationAdmin(CatalogAdmin):
    list_display = ["location_id", "name", "city", "client", "business_account", "is_active", "mapped_to", "account"]
    search_fields = ["location_id", "name", "address", "city"]


@admin.register(PlatformAccount)
class PlatformAccountAdmin(admin.ModelAdmin):
    list_display = ["label", "platform", "client", "is_active", "last_synced_at"]
    list_filter = ["platform", "is_active", "client"]
    autocomplete_fields = ["client"]


class BrandOutletInline(admin.TabularInline):
    model = BrandOutlet
    extra = 1
    fields = ["outlet_name", "area", "city", "zomato", "swiggy", "google", "is_active"]
    autocomplete_fields = ["zomato", "swiggy", "google"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "client", "industry", "outlet_count", "mapped_ids", "is_active"]
    list_filter = ["industry", "is_active", "client"]
    search_fields = ["name", "client__name"]
    autocomplete_fields = ["client"]
    inlines = [BrandOutletInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("client", "industry").annotate(
            n_outlets=Count("outlets"),
            n_zomato=Count("outlets", filter=Q(outlets__zomato__isnull=False)),
            n_swiggy=Count("outlets", filter=Q(outlets__swiggy__isnull=False)),
            n_google=Count("outlets", filter=Q(outlets__google__isnull=False)),
        )

    @admin.display(description="Stores", ordering="n_outlets")
    def outlet_count(self, obj):
        return obj.n_outlets

    @admin.display(description="Zomato / Swiggy / Google")
    def mapped_ids(self, obj):
        return format_html("{} / {} / {}", obj.n_zomato, obj.n_swiggy, obj.n_google)


class BrandInline(admin.TabularInline):
    model = Brand
    extra = 0
    fields = ["name", "industry", "is_active"]
    show_change_link = True


class ClientUserInline(admin.TabularInline):
    model = ClientUser
    extra = 0
    autocomplete_fields = ["user"]
    exclude = ["outlets"]  # assigned on the dashboard's Team page


# platform code -> (catalog model, id field, label, extra column shown)
CLIENT_ID_PLATFORMS = {
    "zomato": (ZomatoOutlet, "res_id", "Zomato", "area"),
    "swiggy": (SwiggyOutlet, "swiggy_id", "Swiggy", "area"),
    "google": (GoogleLocation, "location_id", "Google", "address"),
}
PAGE_SIZE = 100


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_name", "contact_email", "brand_count", "owned_ids", "manage_ids_link", "is_active"]
    search_fields = ["name", "contact_name", "contact_email"]
    readonly_fields = ["manage_ids_link"]
    fields = ["name", "contact_name", "contact_email", "contact_phone", "is_active", "manage_ids_link"]
    inlines = [ClientUserInline, BrandInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_brands=Count("brands", distinct=True),
            n_zomato=Count("zomatooutlet_set", distinct=True),
            n_swiggy=Count("swiggyoutlet_set", distinct=True),
            n_google=Count("googlelocation_set", distinct=True),
        )

    @admin.display(description="Brands", ordering="n_brands")
    def brand_count(self, obj):
        return obj.n_brands

    @admin.display(description="Owned ids Z / S / G")
    def owned_ids(self, obj):
        return format_html("{} / {} / {}", obj.n_zomato, obj.n_swiggy, obj.n_google)

    @admin.display(description="Platform IDs")
    def manage_ids_link(self, obj):
        if not obj or not obj.pk:
            return "Save the client first, then assign its Zomato / Swiggy / Google IDs."
        return format_html('<a class="button" href="{}">Manage IDs</a>', reverse("admin:outlets_client_ids", args=[obj.pk]))

    def get_urls(self):
        return [path("<int:client_id>/ids/", self.admin_site.admin_view(self.manage_ids), name="outlets_client_ids"),
                *super().get_urls()]

    def response_add(self, request, obj, post_url_continue=None):
        # New client: go straight to assigning its ids (unless "Save and add another")
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            self.message_user(request, f"{obj} created. Now assign its Zomato / Swiggy / Google IDs.", messages.SUCCESS)
            return redirect("admin:outlets_client_ids", obj.pk)
        return super().response_add(request, obj, post_url_continue)

    def manage_ids(self, request, client_id):
        """Assign catalog ids to this client, or remove them, one platform tab at a time."""
        client = get_object_or_404(Client, pk=client_id)
        if not self.has_change_permission(request, client):
            raise PermissionDenied
        platform = request.GET.get("platform", "zomato")
        if platform not in CLIENT_ID_PLATFORMS:
            platform = "zomato"
        model, pk, label, extra = CLIENT_ID_PLATFORMS[platform]

        if request.method == "POST":
            ids = request.POST.getlist("ids")
            if request.POST.get("op") == "assign" and ids:
                n = model.objects.filter(pk__in=ids, client__isnull=True).update(client=client)
                self.message_user(request, f"Assigned {n} {label} IDs to {client}.", messages.SUCCESS)
                if n < len(ids):
                    self.message_user(request, f"{len(ids) - n} skipped: they already belong to a client.", messages.WARNING)
            elif request.POST.get("op") == "remove" and ids:
                in_use = model.objects.filter(pk__in=ids, client=client, brand_outlet__isnull=False).count()
                n = model.objects.filter(pk__in=ids, client=client, brand_outlet__isnull=True).update(client=None)
                self.message_user(request, f"Removed {n} {label} IDs from {client}.", messages.SUCCESS)
                if in_use:
                    self.message_user(request, f"{in_use} kept: they are used by one of {client}'s stores. "
                                               "Unmap them from the store first.", messages.WARNING)
            return redirect(request.get_full_path())

        def search(qs, term):
            if term:
                cond = Q(**{f"{pk}__icontains": term}) | Q(name__icontains=term) | Q(city__icontains=term)
                cond |= Q(**{f"{extra}__icontains": term})
                qs = qs.filter(cond)
            return qs

        q_avail = request.GET.get("q", "").strip()
        q_owned = request.GET.get("q2", "").strip()
        available = search(model.objects.filter(client__isnull=True, is_active=True), q_avail).order_by("name", "city")
        owned = (search(model.objects.filter(client=client), q_owned)
                 .select_related("brand_outlet__brand").order_by("name", "city"))
        page_a = Paginator(available, PAGE_SIZE).get_page(request.GET.get("pa"))
        page_o = Paginator(owned, PAGE_SIZE).get_page(request.GET.get("po"))

        def rows(page):
            return [{"id": getattr(o, pk), "name": o.name, "extra": getattr(o, extra), "city": o.city,
                     "is_active": o.is_active, "store": getattr(o, "brand_outlet", None)} for o in page]

        tabs = [{"code": code, "label": lbl,
                 "owned": m.objects.filter(client=client).count(),
                 "available": m.objects.filter(client__isnull=True, is_active=True).count()}
                for code, (m, _, lbl, _) in CLIENT_ID_PLATFORMS.items()]
        return render(request, "admin/outlets/client_ids.html", {
            **self.admin_site.each_context(request),
            "title": f"{client} · platform IDs", "client": client, "opts": self.model._meta,
            "platform": platform, "label": label, "extra_label": extra.replace("_", " ").title(), "tabs": tabs,
            "q": q_avail, "q2": q_owned, "page_a": page_a, "page_o": page_o,
            "available": rows(page_a), "owned": rows(page_o),
        })


@admin.register(ClientUser)
class ClientUserAdmin(admin.ModelAdmin):
    list_display = ["user", "client", "role"]
    list_filter = ["client", "role"]
    autocomplete_fields = ["user", "client"]
    exclude = ["outlets"]  # assigned on the dashboard's Team page


@admin.register(BrandOutlet)
class BrandOutletAdmin(admin.ModelAdmin):
    """Flat view of the whole mapping: every store with its three ids."""

    list_display = ["outlet_name", "brand", "city", "zomato_id", "swiggy_id", "google_id", "is_active"]
    list_filter = ["brand__client", "brand__industry", "is_active", "city"]
    search_fields = ["outlet_name", "brand__name", "city", "zomato__res_id", "swiggy__swiggy_id", "google__location_id"]
    autocomplete_fields = ["brand", "zomato", "swiggy", "google"]
    list_select_related = ["brand"]

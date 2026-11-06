"""Who we serve and what they own.

    platform_accounts                                      logins on each platform: Codeonto master
                                                           accounts (client empty) or a client's own login
    zomato_outlets / swiggy_outlets / google_locations     every outlet id those logins can access; each id
                                                           has an owner client (assigned by staff, or
                                                           automatically when it comes from the client's login)
    clients -> brands                                      the paying company and its brands (custom names)
    client_users                                           which login (Django user) belongs to which client
    brand_outlets                                          THE MAPPING, made by the client: one row = one
                                                           physical store and its Zomato / Swiggy / Google id
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PlatformAccount(TimeStamped):
    """A platform login that gives access to outlets: a Codeonto master account (no client)
    or a client's own login (client set: every id it can access becomes that client's)."""

    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="accounts")
    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, null=True, blank=True,
                               related_name="platform_accounts",
                               help_text="Empty = Codeonto master account. Set = this client's own login.")
    label = models.CharField(max_length=120, help_text="Same name as the collector account, e.g. main, mn, ggn")
    credentials_ref = models.CharField(
        max_length=500, blank=True,
        help_text="Where the session/token lives, never the secret itself: file:/path/cookies.json or env:VAR",
    )
    is_active = models.BooleanField(default=True)
    only_ids = models.JSONField(
        default=list, blank=True,
        help_text="Outlet ids to take from this login, when it can see far more than we serve. Empty = every outlet it can access.")
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_accounts"
        ordering = ["platform", "label"]
        constraints = [models.UniqueConstraint(fields=["platform", "label"], name="uniq_account_label")]

    def __str__(self):
        return f"{self.platform} · {self.label}"


class CatalogOutlet(models.Model):
    """Common fields of the per-platform catalogs. Rows are synced, never typed by hand."""

    name = models.CharField(max_length=255)
    city = models.CharField(max_length=120, blank=True)
    account = models.ForeignKey(PlatformAccount, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="+", help_text="Login this outlet was found in")
    client = models.ForeignKey("outlets.Client", on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="%(class)s_set",
                               help_text="Owner: only this client can map this id to its stores")
    is_active = models.BooleanField(default=True, help_text="False once it disappears from our accounts")
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name", "city"]


class ZomatoOutlet(CatalogOutlet):
    res_id = models.CharField("Zomato res ID", max_length=32, primary_key=True)
    area = models.CharField(max_length=160, blank=True)

    class Meta(CatalogOutlet.Meta):
        db_table = "zomato_outlets"
        verbose_name = "Zomato outlet"

    def __str__(self):
        return f"{self.name} · {self.area or self.city} ({self.res_id})"


class SwiggyOutlet(CatalogOutlet):
    swiggy_id = models.CharField("Swiggy ID", max_length=32, primary_key=True)
    area = models.CharField(max_length=160, blank=True)

    class Meta(CatalogOutlet.Meta):
        db_table = "swiggy_outlets"
        verbose_name = "Swiggy outlet"

    def __str__(self):
        return f"{self.name} · {self.area or self.city} ({self.swiggy_id})"


class GoogleLocation(CatalogOutlet):
    location_id = models.CharField("Google location ID", max_length=255, primary_key=True,
                                   help_text="The number in locations/<id>")
    address = models.TextField(blank=True)
    business_account = models.CharField(max_length=255, blank=True,
                                        help_text="Business Profile account that owns it, e.g. accounts/123 (needed for reviews)")

    class Meta(CatalogOutlet.Meta):
        db_table = "google_locations"
        verbose_name = "Google location"

    def __str__(self):
        return f"{self.name} · {self.city} ({self.location_id})"


class Client(TimeStamped):
    """The company that pays Codeonto. Owns one or more brands."""

    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "clients"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClientUser(TimeStamped):
    """Links a login (Django user) to the client it works for. Staff users need no client: they see everything."""

    ROLE_CHOICES = [("admin", "Client admin"), ("manager", "Manager"), ("viewer", "Viewer")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_membership")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="admin")
    outlets = models.ManyToManyField("BrandOutlet", blank=True, related_name="assigned_users", db_table="client_user_outlets",
                                     help_text="The only outlets a manager can see. Admins and viewers see the whole client.")

    class Meta:
        db_table = "client_users"
        verbose_name = "client user"

    def __str__(self):
        return f"{self.user} · {self.client} ({self.role})"

    @property
    def can_edit(self) -> bool:
        """Can do day-to-day work such as drafting review replies."""
        return self.role in ("admin", "manager")

    @property
    def can_manage(self) -> bool:
        """Can change brands, outlet mapping, platform connections and the team."""
        return self.role == "admin"

    @property
    def is_outlet_limited(self) -> bool:
        return self.role == "manager"


class Brand(TimeStamped):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="brands")
    name = models.CharField(max_length=200, help_text="Shown exactly as the client wants")
    industry = models.ForeignKey("masters.Industry", on_delete=models.PROTECT, related_name="brands")
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["client", "name"], name="uniq_brand_name_per_client")]

    def __str__(self):
        return self.name


class BrandOutlet(TimeStamped):
    """The mapping: a brand's physical store and its platform ids. Each id can belong to one store only."""

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="outlets")
    outlet_name = models.CharField(max_length=200, help_text="e.g. 'Sector 29' or 'Connaught Place'")
    area = models.CharField(max_length=160, blank=True)
    city = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    zomato = models.OneToOneField(ZomatoOutlet, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="brand_outlet", db_column="zomato_res_id", verbose_name="Zomato outlet")
    swiggy = models.OneToOneField(SwiggyOutlet, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="brand_outlet", db_column="swiggy_id", verbose_name="Swiggy outlet")
    google = models.OneToOneField(GoogleLocation, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="brand_outlet", db_column="google_location_id", verbose_name="Google location")
    is_active = models.BooleanField(default=True)

    # platform code -> field name; the single place that knows which platforms map per outlet
    PLATFORM_FIELDS = {"zomato": "zomato", "swiggy": "swiggy", "google": "google"}

    class Meta:
        db_table = "brand_outlets"
        ordering = ["brand__name", "city", "outlet_name"]

    @property
    def display_name(self) -> str:
        """Brand plus whatever tells this store apart, without repeating the brand name."""
        parts = [self.brand.name]
        for v in (self.outlet_name, self.area):
            if v and v.strip().lower() not in {p.strip().lower() for p in parts} and v.strip().lower() not in " ".join(parts).lower():
                parts.append(v.strip())
        return " · ".join(parts)

    def __str__(self):
        return f"{self.brand} · {self.outlet_name}"

    def platform_ids(self) -> dict[str, str | None]:
        return {code: getattr(self, f"{field}_id") for code, field in self.PLATFORM_FIELDS.items()}

    def clean(self):
        """An id can only be mapped by the client that owns it."""
        errors = {}
        for code, field in self.PLATFORM_FIELDS.items():
            item = getattr(self, field)
            if item is None:
                continue
            if item.client_id is None:
                errors[field] = f"{item} is not assigned to any client yet. Assign it to {self.brand.client} first."
            elif item.client_id != self.brand.client_id:
                errors[field] = f"{item} belongs to {item.client}, not {self.brand.client}."
        if errors:
            raise ValidationError(errors)


class LoginCode(models.Model):
    """A one-time login code emailed to a user. Only a hash is stored; it expires after a few minutes, allows a few
    wrong guesses, and works once."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_codes")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "login_codes"
        indexes = [models.Index(fields=["user", "created_at"])]

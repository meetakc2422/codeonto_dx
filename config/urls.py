from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from apps.metrics import api as metrics
from apps.outlets import api as outlets
from apps.outlets import auth_api, staff_api, team_api
from apps.reviews import api as reviews
from apps.stockouts import api as stockouts
from apps.complaints import api as complaints
from apps.insights import api as insights
from apps.uptime import api as uptime
from apps.payouts import api as payouts
from apps.billing import api as billing
from apps.listings import api as listings
from apps.alerts import api as alerts
from apps.integrations import google_oauth
from apps.assistant import api as assistant
from apps.competition import api as competition
from apps.competition import market_api, market_export

admin.site.site_header = "Codeonto admin"
admin.site.site_title = "Codeonto"
admin.site.index_title = "Clients, brands & outlet mapping"

api = [
    path("auth/me", auth_api.me),
    path("auth/login", auth_api.login_view),
    path("auth/logout", auth_api.logout_view),
    path("auth/password", auth_api.change_password),
    path("auth/password/forgot", auth_api.forgot_password),
    path("auth/password/reset", auth_api.reset_password),
    path("staff/clients", staff_api.clients),
    path("staff/clients/<int:client_id>", staff_api.client_detail),
    path("staff/clients/<int:client_id>/ids/<slug:platform>", staff_api.client_ids),
    path("industries", outlets.industries),
    path("clients", outlets.clients),
    path("clients/<int:client_id>/team", team_api.team),
    path("clients/<int:client_id>/team/<int:user_id>", team_api.team_member),
    path("brands", outlets.brands),
    path("brands/<int:brand_id>", outlets.brand_detail),
    path("brands/<int:brand_id>/config", outlets.brand_config),
    path("brands/<int:brand_id>/outlets", outlets.brand_outlets),
    path("brands/<int:brand_id>/outlets/import", outlets.import_outlets),
    path("catalog/<slug:platform>", outlets.catalog),
    path("brands/<int:brand_id>/kpis", metrics.brand_kpis),
    path("brands/<int:brand_id>/kpis/<slug:kpi_code>/trend", metrics.kpi_trend),
    path("brands/<int:brand_id>/leaderboard/<slug:kpi_code>", metrics.leaderboard),
    path("brands/<int:brand_id>/rollups/reviews", metrics.run_review_rollup),
    path("brands/<int:brand_id>/reviews", reviews.brand_reviews),
    path("brands/<int:brand_id>/reviews/summary", reviews.reviews_summary),
    path("reviews/<int:review_id>/replies", reviews.create_reply),
    path("brands/<int:brand_id>/money-leaked", insights.money_leaked),
    path("brands/<int:brand_id>/items", insights.item_scorecard),
    path("brands/<int:brand_id>/complaints", complaints.brand_complaints),
    path("brands/<int:brand_id>/complaints/summary", complaints.complaints_summary),
    path("complaints/<int:complaint_id>", complaints.update_complaint),
    path("brands/<int:brand_id>/stock-outs", stockouts.brand_stock_outs),
    path("brands/<int:brand_id>/stock-outs/summary", stockouts.stock_outs_summary),
    path("brands/<int:brand_id>/stock-outs/export", stockouts.stock_outs_export),
    path("uptime/changes", uptime.uptime_changes),
    path("billing/plans", billing.plans),
    path("billing/quote", billing.plan_quote),
    path("clients/<int:client_id>/billing", billing.client_billing),
    path("clients/<int:client_id>/billing/requests", billing.request_plan),
    path("brands/<int:brand_id>/payouts/summary", payouts.payout_summary),
    path("brands/<int:brand_id>/payouts/cycles", payouts.payout_cycles),
    path("brands/<int:brand_id>/payouts/cycles/<int:cycle_id>", payouts.payout_cycle_detail),
    path("brands/<int:brand_id>/uptime/summary", uptime.uptime_summary),
    path("brands/<int:brand_id>/uptime/episodes", uptime.offline_episodes),
    path("brands/<int:brand_id>/listings", listings.brand_listings),
    path("brands/<int:brand_id>/competition", competition.competition),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/locate", competition.locate),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/suggest", competition.suggest),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/search", competition.search),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/track", competition.track),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/places/<str:place_id>/reviews", competition.place_reviews),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>", market_api.overview),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/locations", market_api.locations),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/area", market_api.set_area),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/peek", market_api.peek),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/search", market_api.search),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/track", market_api.track),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/us", market_api.set_us),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/export", market_export.export),
    path("brands/<int:brand_id>/competition/<int:outlet_id>/<str:platform>/restaurants/<str:res_id>", market_api.restaurant),
    path("google/connect", google_oauth.connect),
    path("assistant/chat", assistant.chat),
    path("google/connections/<int:pk>", google_oauth.disconnect),
    path("clients/<int:client_id>/google", google_oauth.client_connections),
    path("brands/<int:brand_id>/alerts", alerts.brand_alerts),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("g/oauth/callback/", google_oauth.callback),
    path("codeonto/googleservices/oauth/callback/", google_oauth.callback),  # same handler under the api.codeonto.com address
    *[path(f"api/{p.pattern}", p.callback) for p in api],
    # Dashboard (static SPA)
    path("", serve, {"path": "index.html", "document_root": settings.FRONTEND_DIR}),
    re_path(r"^(?P<path>(app\.js|styles\.css|assets/.+))$", serve, {"document_root": settings.FRONTEND_DIR}),
]

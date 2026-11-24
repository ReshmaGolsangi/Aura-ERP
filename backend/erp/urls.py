from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView
from . import views

router = DefaultRouter()
router.register("users", views.UserViewSet)
router.register("customers", views.CustomerViewSet)
router.register("products", views.ProductViewSet)
router.register("targets", views.TargetViewSet)
router.register("proformas", views.ProformaViewSet, basename="proforma")
router.register("receipts", views.ReceiptViewSet, basename="receipt")
router.register("distributors", views.DistributorViewSet)
router.register("distributor-products", views.DistributorProductViewSet, basename="distributorproduct")
router.register("purchase-orders", views.PurchaseOrderViewSet)
router.register("quotations", views.QuotationViewSet, basename="quotation")

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("me/", views.me),
    path("funnel/", views.funnel),
    path("dashboard/", views.dashboard),
    path("", include(router.urls)),
]

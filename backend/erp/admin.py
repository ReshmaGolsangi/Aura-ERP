from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models

admin.site.register(models.User, UserAdmin)
for m in (models.Customer, models.Product, models.Quotation, models.QuotationRevision,
          models.QuotationItem, models.Target, models.NumberSequence,
          models.ProformaInvoice, models.Receipt, models.Distributor, models.DistributorProduct,
          models.PurchaseOrder, models.PurchaseOrderItem):
    admin.site.register(m)

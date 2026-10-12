from django.contrib import admin

from .models import BusinessProcessingStatus, BusinessUser

admin.site.register(BusinessProcessingStatus)
admin.site.register(BusinessUser)

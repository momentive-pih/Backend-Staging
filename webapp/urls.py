from django.urls import path
from . import views
# from . import category_management

urlpatterns = [
    path('products', views.all_products, name='all_products'),
    path('selectedProducts',views.selected_products, name='selected_products'),
    # path('selectedCategories',views.selected_categories, name='selected_categories'),
    # path('basicDetails',category_management.basic_properties, name='basic_properties'),
    # path('productsolr',category_management.solar_connection, name="solar_connection")
]


from django.urls import path
from . import views
from . import category_management

urlpatterns = [
    path('products', views.all_products, name='all_products'),
    path('selectedProducts',views.selected_products, name='selected_products'),
    path('specList',views.get_spec_list, name="get_spec_list"),
    path('homePageData',views.home_page_details, name="home_page_details"),
    path('selectedSpecid',views.set_selected_spec_list,name="set_selected_spec_list"),
    path('getSelectedAttributesData',category_management.get_selected_attributes_data,name="get_selected_attributes_data")
]


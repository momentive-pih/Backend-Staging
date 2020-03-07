from django.urls import path
from . import views
# from . import category_management

urlpatterns = [
    path('products', views.all_products, name='all_products'),
    path('selectedProducts',views.selected_products, name='selected_products'),
    # path('selectedCategories',views.selected_categories, name='selected_categories'),
    # path('basicDetails',category_management.basic_properties, name='basic_properties'),
    path('specList',views.get_spec_list, name="get_spec_list"),
    path('homePageData',views.home_page_details, name="home_page_details")
]


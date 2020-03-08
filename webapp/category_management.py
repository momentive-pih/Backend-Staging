from django.http import HttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.http import HttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q
import json
from . import views
import re
import pandas as pd
import pysolr
from momentive_backend.settings import SOLAR_CONFIGURATION as db_config
from momentive_backend.settings import solr_product,solr_notification_status,solr_unstructure_data,solr_document_variant
selected_spec_id=[]
material_list=[]
@csrf_exempt
def get_selected_attributes_data(requests):
    if requests.method=="POST":
        try:
            global selected_spec_id
            global material_list
            data = requests.body.decode('utf-8')
            data_json=json.loads(data)
            selected_category = data_json.get("category",None).strip()
            print(views.selected_spec_id)
            identified_details=[]
            selected_spec_id = views.selected_spec_id
            material_list = views.selected_material_details
            if selected_category=="sales_information":   
                print("ee",material_list) 
                print("dd",selected_spec_id)          
                identified_details=get_sales_data_details(material_list)
            if selected_category=="report_data":
                identified_details = get_report_data_details(selected_spec_id)
            return JsonResponse(identified_details,content_type="application/json",safe=False)
        except Exception as e:
            print(e)
            return JsonResponse([],content_type="application/json",safe=False)

def get_report_data_details(selected_spec_id):
    try:
        report_list=[]
        for sspecid in selected_spec_id:
            report_column_str="REPTY,RGVID,LANGU,VERSN,STATS,RELON"
            params={"rows":2147483647,"fl":report_column_str}
            query=f'SUBID:{sspecid}'
            result = list(solr_document_variant.search(query,**params))           
            for data in result:
                report_json={
                    "category":data.get("REPTY").strip(),
                    "generation_Variant":data.get("RGVID").strip(),
                    "language":data.get("LANGU").strip(),
                    "version":data.get("VERSN").strip(),
                    "released_on":data.get("RELON").strip(),
                    "spec_id":str(sspecid)
                }
                report_list.append(report_json)
        # print(len(report_list))
        result_data={"reportDataproducts":report_list}
        return result_data
    except Exception as e:
        print(e)
        return []

def get_sales_data_details(material_list):
    try:
        sales_list=[]
        for matid in material_list:
            sales_column_str="DATA_EXTRACT"
            material_number=matid.get("material_number")
            basic_data=matid.get("bdt")
            material_description=matid.get("description")
            specid=matid.get("specid")
            query=f'CATEGORY:SAP-BW && IS_RELEVANT:1 && PRODUCT:{material_number}'
            params={"rows":2147483647,"fl":sales_column_str}
            result = list(solr_unstructure_data.search(query,**params))
            sales_kg=0
            sales_org=[]
            for data in result:             
                data_extract=json.loads(data.get("DATA_EXTRACT"))
                sales_org.append(data_extract.get("Sales Organization"))
                sales_kg=sales_kg+int(data_extract.get("SALES KG"))
            sales_org=list(set(sales_org))
            print(sales_org)
            sales_org=", ".join(sales_org)
            sales_json={
                "Material number":material_number,
                "Material description":material_description,
                "Basic data":basic_data,
                "Sales Org":sales_org,
                "Past Sales":str(sales_kg)+" Kg",
                "Specid":specid
                }
            sales_list.append(sales_json) 
            print("out",sales_list) 
        result_data={"saleDataProducts":sales_list}
        return result_data
    except Exception as e:
        print(e)
        return []


from django.http import HttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django_pandas.io import read_frame
import re
from . import views
import pandas as pd
import pysolr
import json
from momentive_backend.settings import SOLAR_CONFIGURATION as db_config
from momentive_backend.settings import solr_product

product_column = ["TYPE","TEXT1","TEXT2","TEXT3","TEXT4","SUBCT"]
product_nam_category = [["TEXT1","NAM PROD"],["TEXT2","REAL-SPECID"],["TEXT3","SYNONYMS"]]
product_rspec_category = [["TEXT2","REAL-SPECID"],["TEXT1","NAM PROD"],["TEXT3","SYNONYMS"]]
product_namsyn_category = [["TEXT3","SYNONYMS"],["TEXT2","REAL-SPECID"],["TEXT1","NAM PROD"]]
material_number_category = [["TEXT1","MATERIAL NUMBER"],["TEXT3","BDT"],["TEXT4","DESCRIPTION"]]
material_bdt_category = [["TEXT3","BDT"],["TEXT1","MATERIAL NUMBER"],["TEXT4","DESCRIPTION"]]
cas_number_category = [["TEXT1","CAS NUMBER"],["TEXT2","PURE-SPECID"],["TEXT3","CHEMICAL-NAME"]]
cas_pspec_category = [["TEXT2","PURE-SPECID"],["TEXT1","CAS NUMBER"],["TEXT3","CHEMICAL-NAME"]]
cas_chemical_category = [["TEXT3","CHEMICAL-NAME"],["TEXT2","PURE-SPECID"],["TEXT1","CAS NUMBER"]]


@csrf_exempt
def basic_properties(requests):
    try:   
        if requests.method=="GET":
            try:
                # df_product,df_product_combine,product_column = views.inscope_product_details()
                basic_details=[]
                product_level_details=[]
                product_level_dict={}
                material_level_details=[]
                material_level_dict = {}
                cas_level_details=[]
                column_add=[]
                cas_level_dict={}
                product_level_flag=''
                material_level_flag=''
                cas_level_flag=''
                material_id=''
                spec_id_search=''
                material_number=''
                material_desc=''
                count=0
                # basic_df = df_product_combine.copy()
                data_json=views.selected_data_details()
                print(views.selected_data_details())
                for item in data_json:
                    search_value = item.get("name")
                    search_value_split = search_value.split(" | ")
                    search_column = item.get("type")
                    search_key = item.get("key")
                    search_column_split = search_column.split(" | ")
                    search_group = item.get("group").split("(")
                    search_group = search_group[0].strip()
                    column_add.append(search_column)
                    count+=1
                    if search_group == "PRODUCT-LEVEL":
                        product_level_flag = 's'
                        product_count = count
                        product_rspec = search_value_split[search_column_split.index("REAL-SPECID")]
                    if search_group == "MATERIAL-LEVEL":
                        material_level_flag = 's'
                        material_count = count
                        material_number = search_value_split[search_column_split.index("MATERIAL NUMBER")]
                    if search_group == "CAS-LEVEL":
                        cas_level_flag = 's'
                        cas_count = count
                        cas_pspec = search_value_split[search_column_split.index("PURE-SPECID")]

                def product_level_data(data_df,extract_column,product_level_dict,product_level_details):
                    temp_df=data_df[extract_column].values.tolist()
                    for value1,value2,value3 in temp_df:
                        product_level_dict["productName"]=value2
                        product_level_dict["spec_id"]=value1
                        product_level_dict["ProdIdentifiers"]=value2
                        product_level_dict["Synonyms"]=value3
                        active_df=basic_df[(basic_df["TYPE"]=="MATNBR") & (basic_df["TEXT2"]==value1)]
                        len_active_df=len(active_df["TEXT1"].unique())
                        product_level_dict["No_Active_Materials"]=len_active_df
                        product_level_dict["Sales_Volume"]=''
                        product_level_dict["GHS_Information"]=''
                        product_level_dict["tab_modal"]='compositionModal'
                        print(product_level_dict)
                        product_level_details.append(product_level_dict)
                        product_level_dict={}  

                if product_level_flag=='s' and product_count==1:
                    product_temp_df = basic_df[(basic_df["TYPE"]=="NAMPROD") & (basic_df["SUBCT"]=="REAL_SUB") & (basic_df["TEXT2"]==product_rspec)]
                    product_level_data(product_temp_df,["TEXT2","TEXT1","TEXT3"],product_level_dict,product_level_details)

                    # if material_level_flag=='' and cas_level_flag=='':
                    #     print(product_rspec)                        
                    #     #to find material level details
                    #     temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==product_rspec)]
                    #     material_level_data(temp_df)
                    #     # searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    #     #to find cas level details
                    #     temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==product_rspec)]
                    #     column_value = temp_df["TEXT1"].unique()
                    #     temp_df=pd.DataFrame()
                    #     for item in column_value: 
                    #         add_df = edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==item)]
                    #         temp_df=pd.concat([temp_df,add_df])
                    #     print(temp_df)
                    #     #real spec will act as pure spec componant 
                    #     add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["TEXT2"]==product_rspec)]
                    #     temp_df=pd.concat([temp_df,add_df])
                    #     print(temp_df)
                    #     searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                      
                    # elif material_level_flag=='s' and material_count==2 and cas_level_flag=='':
                    #     #to find cas level details
                    #     temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==product_rspec)]
                    #     column_value = temp_df["TEXT1"].unique()
                    #     temp_df=pd.DataFrame()
                    #     for item in column_value:  
                    #         add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==item)]
                    #         temp_df=pd.concat([temp_df,add_df])
                    #     #real spec will act as pure spec componant 
                    #     add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["TEXT2"]==product_rspec)]
                    #     temp_df=pd.concat([temp_df,add_df])
                    #     searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"NUMCAS","PURE_SUB","CAS*","CAS-LEVEL","yes")
                    # elif cas_level_flag=='s' and cas_count==2 and material_level_flag=='':
                        # temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT1"]==cas_pspec)]
                        # column_value = temp_df["TEXT2"].unique()
                        # temp_df=pd.DataFrame()
                        # for item in column_value:
                        #     add_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==item)]
                        #     temp_df=pd.concat([temp_df,add_df])
                        # searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")

                # elif material_level_flag =='s':
                #     if product_level_flag =='' and cas_level_flag=='':
                #         print("mat",material_number)        
                #         temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT1"]==material_number)]
                #         column_value = temp_df["TEXT2"].unique()
                #         temp_df=pd.DataFrame()
                #         for item in column_value:
                #             # product level details
                #             add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                #             #cas level details
                #         temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==item)]
                #         sub_column_value = temp_df["TEXT1"].unique()
                #         temp_df=pd.DataFrame()
                #         for element in sub_column_value:  
                #             add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==element)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")                         
                            
                #     elif product_level_flag =='s' and product_count ==2 and cas_level_flag=='':
                #         temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==product_rspec)]
                #         sub_column_value = temp_df["TEXT1"].unique()
                #         temp_df=pd.DataFrame()
                #         for element in sub_column_value:  
                #             add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==element)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")                         
                            
                #     elif cas_level_flag=='s' and cas_count==2 and product_level_flag=='':
                #         temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT1"]==cas_pspec)]
                #         column_value = temp_df["TEXT2"].unique()
                #         temp_df=pd.DataFrame()
                #         for item in column_value:
                #             add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                            
                #         # elif cas_level_flag=='s' and product_level_flag =='':
                # elif cas_level_flag=='s':
                #     if product_level_flag =='' and material_level_flag=='':
                        
                #         temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT1"]==cas_pspec)]
                #         column_value = temp_df["TEXT2"].unique()
                #         temp_df=pd.DataFrame()
                #         for item in column_value:
                #             add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         #same pure-spec will be act as real-spec
                #         add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["TEXT2"]==cas_pspec)]
                #         temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")
                #         temp_df=pd.DataFrame()
                #         for item in column_value:                             
                #             add_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==item)]
                #             temp_df=pd.concat([temp_df,add_df])
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")

                #     elif product_level_flag =='s' and product_count ==2 and material_level_flag=='':
                #         temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==product_rspec)]
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")

                #     elif material_level_flag=='s' and material_count==2 and product_level_flag=='':
                #         temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT1"]==material_number)]
                #         column_value = temp_df["TEXT2"].unique()
                #         temp_df=pd.DataFrame()
                #         for item in column_value:
                #             # product level details
                #             add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                #             temp_df=pd.concat([temp_df,add_df]) 
                #         #same pure-spec will be act as real-spec
                #         add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["TEXT2"]==cas_pspec)]
                #         temp_df=pd.concat([temp_df,add_df]) 
                #         searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                
                

                basic_details.append({"productLevel":product_level_details})
                basic_details.append({"MaterialLevel":material_level_details})
                basic_details.append({"CasLevel":cas_level_details})       
                return JsonResponse(basic_details,content_type="application/json",safe=False)       
            except Exception as e:
                print(e)
                return JsonResponse([],content_type="application/json",safe=False)
    except Exception as e:
        print(e)

# @csrf_exempt
# def get_spec_list(requests):
#     try:
#         if requests.method=="POST":
#             data_json=views.selected_data_details()
#             return JsonResponse(res,content_type="application/json",safe=False)
#     except Exception as e:
#         print(e)
#         return JsonResponse([],content_type="application/json",safe=False)


from django.http import HttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q
import json
# from django_pandas.io import read_frame
import re
import pandas as pd
import pysolr
from momentive_backend.settings import SOLAR_CONFIGURATION as db_config
from momentive_backend.settings import solr_product,solr_notification_status,solr_unstructure_data
count=0

junk_column=["solr_id","_version_"]
product_column = ["TYPE","TEXT1","TEXT2","TEXT3","TEXT4","SUBCT"]
product_nam_category = [["TEXT1","NAM PROD"],["TEXT2","REAL-SPECID"],["TEXT3","SYNONYMS"]]
product_rspec_category = [["TEXT2","REAL-SPECID"],["TEXT1","NAM PROD"],["TEXT3","SYNONYMS"]]
product_namsyn_category = [["TEXT3","SYNONYMS"],["TEXT2","REAL-SPECID"],["TEXT1","NAM PROD"]]
material_number_category = [["TEXT1","MATERIAL NUMBER"],["TEXT3","BDT"],["TEXT4","DESCRIPTION"]]
material_bdt_category = [["TEXT3","BDT"],["TEXT1","MATERIAL NUMBER"],["TEXT4","DESCRIPTION"]]
cas_number_category = [["TEXT1","CAS NUMBER"],["TEXT2","PURE-SPECID"],["TEXT3","CHEMICAL-NAME"]]
cas_pspec_category = [["TEXT2","PURE-SPECID"],["TEXT1","CAS NUMBER"],["TEXT3","CHEMICAL-NAME"]]
cas_chemical_category = [["TEXT3","CHEMICAL-NAME"],["TEXT2","PURE-SPECID"],["TEXT1","CAS NUMBER"]]
category_with_key=[["NAM*","TEXT1","NAMPROD","REAL_SUB","PRODUCT-LEVEL",product_nam_category],
                ["RSPEC*","TEXT2","NAMPROD","REAL_SUB","PRODUCT-LEVEL",product_rspec_category],
                ["SYN*","TEXT3","NAMPROD","REAL_SUB","PRODUCT-LEVEL",product_namsyn_category],
                ["MAT*","TEXT1","MATNBR","REAL_SUB","MATERIAL-LEVEL",material_number_category],
                ["BDT*","TEXT3","MATNBR","REAL_SUB","MATERIAL-LEVEL",material_bdt_category],
                ["CAS*","TEXT1","NUMCAS","PURE_SUB","CAS-LEVEL",cas_number_category],
                ["CHEMICAL*","TEXT3","NUMCAS","PURE_SUB","CAS-LEVEL",cas_chemical_category], 
                ["PSPEC*","TEXT2","NUMCAS","PURE_SUB","CAS-LEVEL",cas_pspec_category],            
                ["SPEC*","TEXT2","NAMPROD","REAL_SUB","PRODUCT-LEVEL",product_rspec_category],
                ["SPEC*","TEXT2","NUMCAS","PURE_SUB","CAS-LEVEL",cas_pspec_category]]
category_type = ["MATNBR","NUMCAS","NAMPROD"]
search_category = ["TEXT1","TEXT2","TEXT3"]
selected_categories=["BDT*","MAT*","NAM*","CAS*","CHEMICAL*","RSPEC*","PSPEC*","SYN*","SPEC*"]
selected_data_json = {}
db_url=db_config.get("URL")
product_tb=db_config.get("product_core")
spec_count=[]
real_spec_list=[]
spec_id_list=[]
cas_list=[]
material_list=[]
selected_spec_id=[]
home_default_spec_id=[]
selected_material_details=[]

def selected_data_details():
    global selected_data_json
    global real_spec_list
    global spec_count
    global cas_list
    global material_list
    global spec_id_list
    global selected_spec_id
    return selected_data_json,cas_list,material_list,selected_spec_id

def product_level_creation(product_df,product_category_map,type,subct,key,level_name,filter_flag="no"):
    global cas_list
    json_list=[]
    if filter_flag=="no":
        if type !='' and subct !='':
            temp_df=product_df[(product_df["TYPE"]==type) & (product_df["SUBCT"]==subct)]
        else:
            temp_df=product_df[(product_df["TYPE"]==type)]
    else:
        temp_df=product_df
    
    temp_df.drop_duplicates(inplace=True)
    temp_df=temp_df.fillna("-")
    total_count=0
    display_category=''
    json_category=''
    extract_column=[]
    for column,category in product_category_map:
        
        extract_column.append(column) 
        try:
            col_count=list(temp_df[column].unique())
        except KeyError:
            temp_df[column]="-"
            col_count=list(temp_df[column].unique())

        if '-' in col_count:
            col_count = list(filter(('-').__ne__, col_count))
        category_count = len(col_count)
        total_count+=category_count
        display_category+=category+" - "+str(category_count)+" | "
        json_category+= category+" | " 

        #saving cas number globally
        if column=="TEXT1" and category=="CAS NUMBER":
            cas_list=cas_list+list(temp_df[column].unique())
                
    display_category=display_category[:-3] 
    json_category=json_category[:-3]       
    # print(product_category_map)
    # print(display_category)
    # print(json_category)           
    temp_df=temp_df[extract_column].values.tolist()
    for value1,value2,value3 in temp_df:
        value = str(value1).strip() + " | "+str(value2).strip()+" | "+str(value3).strip()
        out_dict={"name":value,"type":json_category,"key":key,"group":level_name+" ("+display_category+")"+" - "+str(total_count) }
        json_list.append(out_dict)
    # print(json_list)
    return json_list

def querying_solr_data(query,params):
    response = solr_product.search(query,**params)
    result = json.dumps(list(response))
    df_product_combine=pd.read_json(result,dtype=str)
    df_product_combine=df_product_combine.fillna("-")
    # print("after",df_product_combine)
    return df_product_combine

@csrf_exempt
def all_products(requests):
    try:
        global selected_data_json
        if requests.method=="POST":
            try:
                data=''
                all_product_list=[]
                data_json=''
                search=''
                search_split=''
                search_key=''
                search_value=''
                key_flag=''
                edit_df=pd.DataFrame()
                data = requests.body.decode('utf-8')
                data_json=json.loads(data)
                params={"rows":2147483647}
                search = data_json.get("SearchData",None).strip()

                if "*" in search:
                    key_flag='s'
                    search_split=search.split('*')
                    search_key=search_split[0]+"*"
                    search_value = search_split[1].strip()
                else:
                    search_value = search
                                   
                search_value = search_value.replace(" ","\ ")                    
                all_product_list=[]
                if key_flag=='s':
                    for key,category,base1,base2,level,combination_category in category_with_key:
                        if key==search_key.upper():                                                  
                            if len(search_value)>0:                             
                                query=f'{category}:{search_value}*'
                                df_product_combine=querying_solr_data(query,params)
                            else:
                                query=f'TYPE:{base1}'
                                df_product_combine=querying_solr_data(query,params)
                            all_product_list=all_product_list+product_level_creation(df_product_combine,combination_category,base1,base2,key,level)                  
                elif len(search)>=2:
                    for item in search_category:
                        query=f'{item}:{search_value}*'
                        df_product_combine=querying_solr_data(query,params)
                        if len(df_product_combine)>0:
                            if item=="TEXT2": 
                                #for real specid 
                                all_product_list=all_product_list+product_level_creation(df_product_combine,product_rspec_category,"NAMPROD","REAL_SUB","RSPEC*","PRODUCT-LEVEL")
                                #cas level details    
                                all_product_list=all_product_list+product_level_creation(df_product_combine,cas_pspec_category,"NUMCAS","PURE_SUB","PSEPC*","CAS-LEVEL")
                            elif item=="TEXT1":
                                for ctype in category_type:
                                    if ctype=="MATNBR":
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,material_number_category,"MATNBR",'',"MAT*","MATERIAL-LEVEL")
                                    elif ctype=="NUMCAS":
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,cas_number_category,"NUMCAS","PURE_SUB","CAS*","CAS-LEVEL")
                                    else:
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,product_nam_category,"NAMPROD","REAL_SUB","NAM*","PRODUCT-LEVEL")
                            else:
                                for ctype in category_type:
                                    if ctype == "MATNBR":
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,material_bdt_category,"MATNBR",'',"BDT*","MATERIAL-LEVEL")
                                    elif ctype == "NAMPROD":
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,product_namsyn_category,"NAMPROD","REAL_SUB","SYN*","PRODUCT-LEVEL")
                                    else:
                                        all_product_list=all_product_list+product_level_creation(df_product_combine,cas_chemical_category,"NUMCAS","PURE_SUB","CHEMICAL*","CAS-LEVEL")
                    
                return JsonResponse(all_product_list,content_type="application/json",safe=False)
            except Exception as e:
                print(e)
                return JsonResponse([],content_type="application/json",safe=False)
    except Exception as e:
        print(e)
        return JsonResponse([],content_type="application/json",safe=False)

@csrf_exempt
def selected_products(requests):
    try:
        global selected_data_json
        global real_spec_list
        global spec_count
        global cas_list
        global spec_id_list
        if requests.method=="POST":
            try:
                edit_df=pd.DataFrame()
                searched_product_list=[]
                data=''
                count=0
                params={"rows":2147483647}
                product_count=0
                material_count=0
                cas_count=0
                data_json=''
                column_add=[]
                product_level_flag=''
                material_level_flag=''
                cas_level_flag=''
                add_df=pd.DataFrame()
                data = requests.body.decode('utf-8')
                data_json=json.loads(data)
                selected_data_json=data_json
                print("selectedproducts",data_json)
                if len(data_json)<=2:
                    real_spec_list=[]
                    material_list=[]
                    cas_list=[]
                    spec_count=0
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
                            product_name = search_value_split[search_column_split.index("NAM PROD")]
                        if search_group == "MATERIAL-LEVEL":
                            material_level_flag = 's'
                            material_count = count
                            material_number = search_value_split[search_column_split.index("MATERIAL NUMBER")]
                        if search_group == "CAS-LEVEL":
                            cas_level_flag = 's'
                            cas_count = count
                            cas_pspec = search_value_split[search_column_split.index("PURE-SPECID")]
                               
                    if product_level_flag=='s' and product_count==1:
                        #######################
                        spec_count=spec_count+1
                        spec_id_list.append(product_rspec)
                        val_json={"name":(str(product_rspec)+" | "+product_name),"id":spec_count}
                        real_spec_list.append(val_json)
                        print(real_spec_list)
                        #######################
                        if material_level_flag=='' and cas_level_flag=='':                     
                            print(product_rspec)     
                            query=f'TYPE:MATNBR && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params)
                            #to find material level details
                            searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                            #to find cas level details
                            query=f'TYPE:SUBIDREL && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params)                       
                            column_value = temp_df["TEXT1"].unique()
                            temp_df=pd.DataFrame()
                            for item in column_value: 
                                # print(item)
                                query=f'TYPE:NUMCAS && SUBCT:PURE_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)
                                # add_df = edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df])
                            # print("kk",temp_df)
                            #real spec will act as pure spec componant
                            query=f'TYPE:NUMCAS && TEXT2:{product_rspec}'
                            add_df=querying_solr_data(query,params)
                            # add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["TEXT2"]==product_rspec)]
                            temp_df=pd.concat([temp_df,add_df])
                            # print(temp_df)
                            searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                            
                        elif material_level_flag=='s' and material_count==2 and cas_level_flag=='':
                            #to find cas level details
                            print("matdddd",product_rspec)
                            query=f'TYPE:SUBIDREL && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params)
                            column_value = temp_df["TEXT1"].unique()
                            print("column_value",column_value)
                            temp_df=pd.DataFrame()
                            for item in column_value: 
                                query=f'TYPE:NUMCAS && SUBCT:PURE_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params) 
                                # add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df])
                            print("fter",temp_df)
                            #real spec will act as pure spec componant 
                            query=f'TYPE:NUMCAS && TEXT2:{product_rspec}'
                            add_df=querying_solr_data(query,params)
                            print("last",add_df)
                            # add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["TEXT2"]==product_rspec)]
                            temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"NUMCAS","PURE_SUB","CAS*","CAS-LEVEL","yes")
                            print(searched_product_list)
                        elif cas_level_flag=='s' and cas_count==2 and material_level_flag=='':
                            query=f'TYPE:MATNBR && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params)
                            #to find material level details
                            searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    elif material_level_flag =='s' and material_count==1:
                        if product_level_flag =='' and cas_level_flag=='':
                            query=f'TYPE:MATNBR && TEXT1:{material_number}'
                            temp_df=querying_solr_data(query,params)
                            print("mat",material_number)        
                            # temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT1"]==material_number)]
                            column_value = temp_df["TEXT2"].unique()
                            temp_df=pd.DataFrame()
                            for item in column_value:
                                # product level details
                                query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)
                                # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                                #############################                      
                                val_df=add_df[["TEXT2","TEXT1"]]                        
                                val_df.drop_duplicates(inplace=True)
                                val_df=val_df.values.tolist()
                                print(val_df)
                                for spec,nam in val_df:
                                    spec_count+=1
                                    spec_id_list.append(spec)
                                    val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                    real_spec_list.append(val_json)
                                ############################
                                temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                                #cas level details
                            for item in column_value:
                                query=f'TYPE:SUBIDREL && TEXT2:{item}'
                                temp_df=querying_solr_data(query,params)
                                # temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==item)]
                                sub_column_value = temp_df["TEXT1"].unique()
                                temp_df=pd.DataFrame()
                                for element in sub_column_value: 
                                    query=f'TYPE:NUMCAS && TEXT2:{element} && SUBCT:PURE_SUB'
                                    add_df=querying_solr_data(query,params) 
                                    # add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==element)]
                                    temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")                         
                                
                        elif product_level_flag =='s' and product_count ==2 and cas_level_flag=='':
                            #######################
                            spec_count+=1
                            spec_id_list.append(product_rspec)
                            val_json={"name":(str(product_rspec)+" | "+product_name),"id":spec_count}
                            real_spec_list.append(val_json)
                            #######################
                            query=f'TYPE:SUBIDREL && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params) 
                            # temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT2"]==product_rspec)]
                            sub_column_value = temp_df["TEXT1"].unique()
                            temp_df=pd.DataFrame()
                            for element in sub_column_value:
                                query=f'TYPE:NUMCAS && TEXT2:{element} && SUBCT:PURE_SUB'
                                add_df=querying_solr_data(query,params)   
                                # add_df=edit_df[(edit_df["TYPE"]=="NUMCAS") & (edit_df["SUBCT"]=="PURE_SUB") & (edit_df["TEXT2"]==element)]
                                temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")                         
                                
                        elif cas_level_flag=='s' and cas_count==2 and product_level_flag=='':
                            query=f'TYPE:MATNBR && TEXT1:{material_number}'
                            temp_df=querying_solr_data(query,params)
                            print("mat",material_number)        
                            # temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT1"]==material_number)]
                            column_value = temp_df["TEXT2"].unique()
                            temp_df=pd.DataFrame()
                            for item in column_value:
                                #############################  
                                # product level details
                                query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)                    
                                val_df=add_df[["TEXT2","TEXT1"]]                        
                                val_df.drop_duplicates(inplace=True)
                                val_df=val_df.values.tolist()
                                print(val_df)
                                for spec,nam in val_df:
                                    spec_count+=1
                                    spec_id_list.append(spec)
                                    val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                    real_spec_list.append(val_json)
                                ############################
                                query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)
                                # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                                                  
                    elif cas_level_flag=='s' and cas_count==1:
                        if product_level_flag =='' and material_level_flag=='':
                            query=f'TYPE:SUBIDREL && TEXT1:{cas_pspec}'
                            temp_df=querying_solr_data(query,params)
                            # temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT1"]==cas_pspec)]
                            column_value = temp_df["TEXT2"].unique()
                            temp_df=pd.DataFrame()
                            for item in column_value:
                                query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)
                                #############################
                                val_df=add_df[["TEXT2","TEXT1"]]
                                val_df.drop_duplicates(inplace=True)
                                val_df=val_df.values.tolist()
                                for spec,nam in val_df:
                                    spec_count+=1
                                    spec_id_list.append(spec)
                                    val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                    real_spec_list.append(val_json)
                                ############################
                                # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df])
                            #same pure-spec will be act as real-spec
                            query=f'TYPE:NAMPROD && TEXT2:{cas_pspec}'
                            add_df=querying_solr_data(query,params)
                            # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["TEXT2"]==cas_pspec)]
                            temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")
                            temp_df=pd.DataFrame()
                            for item in column_value:
                                query=f'TYPE:MATNBR && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)                          
                                # add_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df])
                            searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")

                        elif product_level_flag =='s' and product_count ==2 and material_level_flag=='':
                            #######################
                            spec_count+=1
                            spec_id_list.append(product_rspec)
                            val_json={"name":(str(product_rspec)+" | "+product_name),"id":spec_count}
                            real_spec_list.append(val_json)
                            #######################
                            query=f'TYPE:MATNBR && TEXT2:{product_rspec}'
                            temp_df=querying_solr_data(query,params)
                            # temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==product_rspec)]
                            searched_product_list=searched_product_list+product_level_creation(temp_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")

                        elif material_level_flag=='s' and material_count==2 and product_level_flag=='':
                            query=f'TYPE:MATNBR && TEXT1:{material_number}'
                            temp_df=querying_solr_data(query,params)
                            # temp_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT1"]==material_number)]
                            column_value = temp_df["TEXT2"].unique()
                            temp_df=pd.DataFrame()
                            for item in column_value:
                                # product level details
                                query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:{item}'
                                add_df=querying_solr_data(query,params)
                                #############################
                                val_df=add_df[["TEXT2","TEXT1"]]
                                val_df.drop_duplicates(inplace=True)
                                val_df=val_df.values.tolist()
                                for spec,nam in val_df:
                                    spec_count+=1
                                    spec_id_list.append(spec)
                                    val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                    real_spec_list.append(val_json)
                                ############################
                                # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                                temp_df=pd.concat([temp_df,add_df]) 
                            #same pure-spec will be act as real-spec
                            # query=f'TYPE:NAMPROD && TEXT2:{cas_pspec}'
                            # add_df=querying_solr_data(query,params)
                            # # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["TEXT2"]==cas_pspec)]
                            # temp_df=pd.concat([temp_df,add_df]) 
                            searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                return JsonResponse(searched_product_list,content_type="application/json",safe=False)     
            except Exception as e:
                print(e)
                return JsonResponse([],content_type="application/json",safe=False)
    except Exception as e:
        print(e)
        return JsonResponse([],content_type="application/json",safe=False)

@csrf_exempt
def get_spec_list(requests):
    if requests.method=="GET":
        global home_default_spec_id
        if len(real_spec_list)>0:
            home_default_spec_id=[]
            home_default_spec_id.append(real_spec_list[0])
        return JsonResponse(real_spec_list,content_type="application/json",safe=False)

@csrf_exempt       
def home_page_details(requests):
    if requests.method=="GET":
        global selected_data_json
        global real_spec_list
        global spec_count
        global cas_list
        global material_list
        global spec_id_list
        global home_default_spec_id
        home_page_details={}
        if len(home_default_spec_id)>0:
            print(material_list)
            cas_list=list(set(cas_list))
            # print(cas_list)
            product_attributes=[]
            bdt_list=[]
            namprod_list=[]
            product_compliance=[]
            customer_comm=[]
            toxicology=[]
            restricted_sub=[]
            sales_information=[]
            report_data=[]
            home_spec_details=home_default_spec_id[0].get("name").split(" | ")
            home_spec=home_spec_details[0]
            home_namprod=home_spec_details[1]
            print(home_spec_details)
            print(home_namprod)          
            #product attributes
            params={"rows":2147483647,"fl":"TEXT1,TEXT2,TEXT3,TEXT4"}
            query=f'TYPE:MATNBR && TEXT2:{home_spec}'
            matinfo=solr_product.search(query,**params)
            matstr=[]
            for i in list(matinfo):
                bdt=str(i.get("TEXT3")).strip()
                bdt_list.append(bdt)
                matnumber=str(i.get("TEXT1"))
                material_list.append(matnumber)
                
                desc=str(i.get("TEXT4"))
                if bdt:
                    bstr=bdt+" - "+matnumber+" - "+desc
                    matstr.append(bstr)
            material_list=list(set(material_list))
            print(material_list)
            bdt_list=list(set(bdt_list))
            if len(matstr)>3:
                matstr=", ".join(matstr[0:2])  
            else:
                matstr=", ".join(matstr)              
            product_attributes.append({"image":"https://5.imimg.com/data5/CS/BR/MY-3222221/pharmaceuticals-chemicals-500x500.jpg"})
            product_attributes.append({"Product Identification": str(home_spec)+"-"+str(home_namprod)})
            product_attributes.append({"Material Information":str(matstr)})
            product_attributes.append({"tab_modal": "compositionModal"})
            home_page_details["Product Attributes"]=product_attributes

            #product compliance
            query=f'SUBID:{home_spec}'
            params={"rows":2147483647,"fl":"RLIST"}
            pcomp=list(solr_notification_status.search(query,**params))
            country=[]
            for r in pcomp:
                place=r.get("RLIST")
                country.append(place)
            rlist=", ".join(country)
            product_compliance.append({"image":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3WDKemmPJYhXsoGknA6nJwlRZTQzuYBY4xmpWAbInraPIJfAT"})
            product_compliance.append({"Negative Regulatory Notification Lists":str(rlist)}) 
            product_compliance.append({"tab_modal": "complianceModal"})          
            #ag registartion
            ag_reglist=[]
            # query=f'CATEGORY:EU_REG_STATUS && IS_RELEVANT:1 && PRODUCT:{home_namprod}'
            # params={"rows":2147483647}
            # usfda=list(solr_unstructure_data.search(query,**params))
            ag_country=''
            product_compliance.append({"AG Registration Status":ag_country})
            home_page_details["Product compliance"]=product_compliance

            #customer communication
            usfda=[]
            eufda=[]
            usflag="No"
            euflag="No"
            query=f'CATEGORY:US-FDA && IS_RELEVANT:1 && PRODUCT:{home_namprod}'
            params={"rows":2147483647}
            usfda=list(solr_unstructure_data.search(query,**params))
            if len(usfda)==0:
                for b in bdt_list:
                    query=f'CATEGORY:US-FDA && IS_RELEVANT:1 && PRODUCT:{b}'
                    params={"rows":2147483647}
                    usfda=list(solr_unstructure_data.search(query,**params))
                    if len(usfda)>0:
                        usflag="Yes"
                        break
            else:
                usflag="Yes"
            query=f'CATEGORY:EU-FDA && IS_RELEVANT:1 && PRODUCT:{home_namprod}'
            params={"rows":2147483647}
            eufda=list(solr_unstructure_data.search(query,**params))
            if len(eufda)==0:
                for b in bdt_list:
                    query=f'CATEGORY:EU-FDA && IS_RELEVANT:1 && PRODUCT:{b}'
                    params={"rows":2147483647}
                    eufda=list(solr_unstructure_data.search(query,**params))
                    if len(eufda)>0:
                        euflag="Yes"
                        break
            else:
                euflag="Yes"        
            customer_comm.append({"image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQzuuf2CXVDH2fVLuKJRbIqd14LsQSAGaKb7_hgs9HAOtSsQsCL"})
            customer_comm.append({"US FDA Compliance" : usflag})
            customer_comm.append({"EU Food Contact " : euflag})
            customer_comm.append({"Top 3 Heavy Metal compositions":""})
            customer_comm.append({"tab_modal": "communicationModal"})
            home_page_details["Customer Communication"]=customer_comm

            #toxicology
            toxicology.append({ "image" : "https://flaptics.io/images/yu.png"})
            toxicology.append({"Study Titles" : ""})
            toxicology.append({"Toxicology Summary Report Available" : ""})
            toxicology.append({"Pending Monthly Tox Studies": ""})
            toxicology.append({ "tab_modal": "toxicologyModal"})
            home_page_details["Toxicology"]=toxicology

            #restricted_sub
            gadsl=[]
            gadsl_fg='No'
            calprop=[]
            cal_fg="No"
            for cas in cas_list:
                query=f'CATEGORY:GADSL && IS_RELEVANT:1 && PRODUCT:{cas}'
                params={"rows":2147483647}
                gadsl=list(solr_unstructure_data.search(query,**params))
                if len(gadsl)>0:
                    gadsl_fg='Yes'
                    break
            for cas in cas_list:
                query=f'CATEGORY:CAL-PROP && IS_RELEVANT:1 && PRODUCT:{cas}'
                params={"rows":2147483647}
                calprop=list(solr_unstructure_data.search(query,**params))
                if len(calprop)>0:
                    cal_fg='Yes'
                    break
            restricted_sub.append({"image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQnJXf4wky23vgRlLzdkExEFrkakubrov2OWcG9DTmDA1zA2-U-"})
            restricted_sub.append({"Components Present in GADSL": gadsl_fg})
            restricted_sub.append({"Components Present in Cal Prop 65":cal_fg})
            restricted_sub.append({"tab_modal": "restrictedSubstanceModal" })
            home_page_details["Restricted Substance"]=restricted_sub

            #sales_information
            kg=0
            sales_country=[]
            sales_information.append({"image":"https://medschool.duke.edu/sites/medschool.duke.edu/files/styles/interior_image/public/field/image/reports.jpg?itok=F7UK-zyt"})
            for mat in material_list:
                print(mat)
                query=f'CATEGORY:SAP-BW && IS_RELEVANT:1 && PRODUCT:{mat}'
                params={"rows":2147483647,"fl":"DATA_EXTRACT"}
                salesinfo=list(solr_unstructure_data.search(query,**params))
                for data in salesinfo:
                    datastr=json.loads(data.get("DATA_EXTRACT"))
                    sales_country.append(datastr.get('Sold-to Customer Country'))
                    # print(datastr.get("SALES KG"))              
                    kg=kg+int(datastr.get("SALES KG"))
            sales_country=list(set(sales_country))
            if len(sales_country)<5:
                sold_country=", ".join(sales_country)
            else:
                sold_country=", ".join(sales_country[0:5])
                sold_country=sold_country+" more.."
            sales_kg=str(kg)+" Kg"
            sales_information.append({"Total sales in 2019" :sales_kg})
            sales_information.append({"Regions where sold" :sold_country})
            sales_information.append({"tab_modal": "salesModal"})
            home_page_details["Sales Information"]=sales_information

            #report data
            report_data.append({ "image":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSReXGibHOlD7Z5nNqD4d4V52CVMmi-fGUEKMH2HE7srV_SzNn_g"})
            report_data.append({"Report Status" :""})
            report_data.append({"tab_modal": "reportModal" })
            home_page_details["Report Data"]=report_data

        return JsonResponse(home_page_details,content_type="application/json",safe=False)

@csrf_exempt
def set_selected_spec_list(requests):
    if requests.method=="POST":
        global selected_spec_id
        global selected_material_details
        global home_default_spec_id
        data = requests.body.decode('utf-8')
        data_json=json.loads(data)
        namprod=[]
        selected_spec_id=[]
        selected_material_details=[]
        if len(data_json)>0:
            home_default_spec_id=[]
            home_default_spec_id.append(data_json[0])
        for spec in data_json:
            spec_details=spec.get("name").split(" | ")
            selected_spec_id.append(spec_details[0])
            params={"rows":2147483647,"fl":"TEXT1,TEXT2,TEXT3,TEXT4"}
            query=f'TYPE:MATNBR && TEXT2:{spec_details[0]}'
            matinfo=solr_product.search(query,**params)
            matstr=[]
            for i in list(matinfo):
                bdt=str(i.get("TEXT3")).strip()
                matnumber=str(i.get("TEXT1"))
                material_list.append(matnumber)              
                desc=str(i.get("TEXT4"))
                matjson={
                    "bdt":bdt,
                    "material_number":matnumber,
                    "description":desc,
                    "specid":str(spec_details[0])
                }
                selected_material_details.append(matjson)               
            namprod.append(spec_details[1])
        selected_spec_id=list(set(selected_spec_id))
        return JsonResponse(selected_spec_id,content_type="application/json",safe=False) 

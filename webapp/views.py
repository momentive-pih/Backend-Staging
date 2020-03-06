from django.http import HttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q
import json
from django_pandas.io import read_frame
import re
import pandas as pd
import pysolr
from momentive_backend.settings import SOLAR_CONFIGURATION as db_config
from momentive_backend.settings import solr_product
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
                
df_product = pd.read_excel(r"C:\Users\MANICKAMM\Desktop\product_info_V2.xlsx",sheet_name="Sheet1")
selected_data_json = {}
db_url=db_config.get("URL")
product_tb=db_config.get("product_core")
spec_count=[]
real_spec_list=[]

def selected_data_details():
    global selected_data_json
    return selected_data_json

def product_level_creation(product_df,product_category_map,type,subct,key,level_name,filter_flag="no"):
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
                elif len(search)>=3:
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
        if requests.method=="POST":
            try:
                real_spec_list=[]
                spec_count=0
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

                print("product_level_flag",product_level_flag)
                print("product_count",product_count)
                print("materialflag",material_level_flag)
                print("material_count",material_count)
                print("cas_level_flag",cas_level_flag)
                print("cas_count",cas_count)              
                if product_level_flag=='s' and product_count==1:
                    if material_level_flag=='' and cas_level_flag=='':
                        #######################
                        spec_count=spec_count+1
                        val_json={"name":(str(product_rspec)+" | "+product_name),"id":spec_count}
                        real_spec_list.append(val_json)
                        print(real_spec_list)
                        #######################
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
                        ##############################
                        spec_count+=1
                        val_json={"name":(str(product_rspec)+" | "+product_name),"id":spec_count}
                        real_spec_list.append(val_json)
                        ###############################
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
                        query=f'TYPE:SUBIDREL && TEXT1:{cas_pspec}'
                        temp_df=querying_solr_data(query,params)
                        # temp_df=edit_df[(edit_df["TYPE"]=="SUBIDREL") & (edit_df["TEXT1"]==cas_pspec)]
                        column_value = temp_df["TEXT2"].unique()
                        temp_df=pd.DataFrame()
                        for item in column_value:
                            ####################
                            query=f'TYPE:NAMPROD && TEXT2:{item} && SUBCT:REAL_SUB'
                            params={"rows":2147483647,"fl":"TEXT1,TEXT2"}
                            val_df=querying_solr_data(query,params)
                            val_df=val_df[["TEXT2","TEXT1"]]
                            val_df.drop_duplicates(inplace=True)
                            val_df=val_df.values.tolist()
                            for spec,nam in val_df:
                                spec_count+=1
                                val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                real_spec_list.append(val_json)
                            #####################
                            query=f'TYPE:MATNBR && TEXT2:{item}'
                            add_df=querying_solr_data(query,params)
                            # add_df=edit_df[(edit_df["TYPE"]=="MATNBR") & (edit_df["TEXT2"]==item)]
                            temp_df=pd.concat([temp_df,add_df])
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
                                val_json={"name":(str(spec)+" | "+str(nam)),"id":spec_count}
                                real_spec_list.append(val_json)
                            ############################
                            # add_df=edit_df[(edit_df["TYPE"]=="NAMPROD") & (edit_df["SUBCT"]=="REAL_SUB") & (edit_df["TEXT2"]==item)]
                            temp_df=pd.concat([temp_df,add_df])
                        searched_product_list=searched_product_list+product_level_creation(temp_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                            
                        # elif cas_level_flag=='s' and product_level_flag =='':
                
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

def get_spec_list(requests):
    if requests.method=="GET":
        return JsonResponse(real_spec_list,content_type="application/json",safe=False)
        
        

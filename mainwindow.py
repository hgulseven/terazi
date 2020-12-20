import datetime
import decimal
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *
import PIL
import pymysql.cursors
import requests
import traceback

import serial
from PIL import Image
from barcode import EAN13
from barcode.writer import ImageWriter
from escpos.printer import Usb

glb_version_str = "2.0"
glb_cursor = 0  # global cursor for db access. Initialized in load_products
glb_customer_no = 0  # customer no is got by using salescounter table.
glb_filter_data = ""
glb_screensize = 1200
top = None
glb_product_names = []  # products are loaded to memory based on rayon
glb_reyonlar = []  # rayon combobox contents
glb_employees = []  # employees loaded to this global collection
glb_sales = []  # sales for the active customer loaded to this collection
glb_active_served_customers = []  # active customers loaded to this collection
glb_customers_on_cashier = []  # customers that were sent to cashier. Actively waiting for payment
# product frame is used for various selections such as Products, Customers
# employees, customer callback if the value is
# 0: employees
# 1: products
# 2: Customers
# 3:Call back customers
# this variable is used for next, previous buttons and set when page display content is changed
glb_webHost = "https://192.168.1.45"
glb_locationid = ""
glb_customer_window = 0
glb_serial_object = None
glb_serialthread = None
glb_merge_customer_flag = None
MERGE_CUSTOMERS = 1
w = None
top_level=None
root = None

glb_active_product_frame_content = 0  # shows contents of product frame which is used more than one purpose
glb_scaleId = 0
glb_employees_selected = ''  # name of the selected employee.
glb_sales_line_id = 1  # line of the sales
glb_base_weight = 0  # tare weight is stored in this variable. Updated when tare button is clicked.
glb_product_page_count = 0  # paging of product buttons displayed in product frame
glb_employees_page_count = 0  # paging of employee buttons displayed in product frame
glb_active_customers_page_count = 0  # paging of active customers buttons displayed in product frame
glb_callback_customers_page_count = 0  # paging of callback customers buttons displayed in product frame

def add_to_log(function, err):

    if sys.platform == "win32":
        logpath = "c:\\users\\hakan\\PycharmProjects\\terazi\\"
    else:
        logpath = "/home/pi/PycharmProjects/terazi/"
    if os.path.isfile(logpath+'log.txt'):
        fsize = os.stat(logpath+'log.txt').st_size
        if fsize > 50000:
            os.rename(logpath+'log.txt', logpath+'log1.txt')
    with open(logpath+'log.txt', 'a') as the_file:
        current_date = datetime.now()
        the_file.write(current_date.strftime("%Y-%m-%d %H:%M:%S") + " " + function + " " + format(err) + "\n")
    the_file.close()

class Product(object):
    def __init__(self, Name=None, price=None, teraziID=None, productBarcodeID=None):
        self.Name = Name
        self.price = price
        self.teraziID = teraziID
        self.productBarcodeID=productBarcodeID

class Customer(object):
    def __init__(self, customer_no=None):
        self.Name = customer_no

class Reyon(object):
    def __init__(self, teraziID=None, ReyonName=None):
        self.teraziID = teraziID
        self.ReyonName = ReyonName

class Employee(object):
    def __init__(self, personelID=None, Name=None):
        self.personelID = personelID
        self.Name = Name

class Sales(object):
    def __init__(self, salesID=None, salesLineID=None, personelID=None, Name=None,
                 retailPrice=None, amount=None, typeOfCollection=None, productBarcodeID=None, productID=None):
        global glb_base_weight
        global glb_locationid

        my_date = datetime.now()
        self.saleDate = my_date.strftime('%Y-%m-%d')
        self.salesID = salesID
        self.salesLineID = salesLineID
        self.personelID = personelID
        self.Name = Name
        self.productID=productID
        self.retailPrice = retailPrice
        self.amount = amount
        self.typeOfCollection = typeOfCollection
        # -1 active customer still being served;
        # -2 customer sales canceled;
        # -3 merged customer
        # 0 send to cashier waiting for payment;
        # 1 paid in cash;
        # 2 paid by credit card;
        # 3 other type of payment;
        self.locationID = glb_locationid
        self.dara = glb_base_weight
        self.productBarcodeID=productBarcodeID

class SalesCounter(object):
    def __init__(self, salesDate=None, counter=None):
        self.salesDate = salesDate
        self.counter = 0

    def get_counter(self,wndHandle):
        global glb_SelectCounter
        global glb_UpdateCounter
        global glb_InsertCounter
        global glb_locationid
        counter = 0
        error = ""
        returnvalue = False

        if db_interface.interface_up:
            my_date = datetime.now()
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectCounter, (my_date.strftime('%Y-%m-%d'), glb_locationid,))
            if error == "":
                number_of_rows = 0
                for row in rows:
                    number_of_rows = number_of_rows + 1
                    counter = row[0] + 1
                if number_of_rows > 0:
                    error = db_interface.db_core.execnonesql(db_interface.glb_UpdateCounter, (counter, my_date.strftime('%Y-%m-%d'), glb_locationid,))
                else:
                    counter = 1
                    error = db_interface.db_core.execnonesql(db_interface.glb_InsertCounter, (my_date.strftime('%Y-%m-%d'), counter, glb_locationid,))
                if error == "":
                    error = db_interface.db_core.commit()
                    if error == "":
                        returnvalue=True
                    else:
                        db_interface.sql_error(wndHandle, error)
                else:
                    db_interface.sql_error(wndHandle, error)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
            counter = -1
        return returnvalue, counter

class dbCore(object):
    glb_host = "192.168.1.45"
    glb_database = "order_and_sales"
    glb_user = "hakan"
    glb_password = "QAZwsx135"
    conn=None
    cursor=None

    def init(self):
        pass

    def connect(self):
        error = ""
        try:
            dbCore.conn = pymysql.connect(host=dbCore.glb_host,
                                   database=dbCore.glb_database,
                                   user=dbCore.glb_user,
                                   password=dbCore.glb_password)  # pyodbc.connect(glb_connection_str)
        except Exception:
            error = traceback.format_exc()
        if dbCore.conn is None:
            error = "SQL bağlantısı oluşturulamadı."
        else:
            dbCore.cursor = dbCore.conn.cursor()
        return error

    def execsql(self,sql_command,sql_params):
        error= ""
        rows = None
        try:
            dbCore.cursor.execute(sql_command, sql_params)
            rows = dbCore.cursor.fetchall()
        except Exception as e:
            error=""
            for arg in e.args:
                if isinstance(arg, int):
                    error = error+" "+str(arg)
                else:
                    error = error+" "+arg
        return error,rows

    def execnonesql(self,sql_command,sql_params):
        error = ""
        try:
            dbCore.cursor.execute(sql_command, sql_params)
        except Exception as e:
            error=""
            for arg in e.args:
                if isinstance(arg, int):
                    error = error+" "+str(arg)
                else:
                    error = error+" "+arg
        return error

    def commit(self):
        error = ""
        try:
            dbCore.conn.commit()
        except Exception as e:
            error = e.args[0]
        return error

    def disconnect(self):
        dbCore.cursor.close()
        dbCore.conn.close()

class db_interface(object):





    # queries
    glb_getversion = "select versionstr from versiontable"
    glb_GetTeraziProducts = "Select  TeraziID, productName, productRetailPrice,barcodeID from teraziscreenmapping left outer join " \
                            "products on (teraziscreenmapping.barcodeID=products.productBarcodeID) where TeraziID=%s order by screenSeqNo;"
    glb_SelectTerazi = "Select  TeraziID, teraziName from terazitable;"
    glb_SelectEmployees = "Select personelID, persName,persSurname  from  employeesmodels;"
    glb_SelectCounter = "select counter from salescounter where salesDate=%s and locationID=%s;"
    glb_UpdateCounter = "Update salescounter set counter=%s where salesDate=%s and locationID=%s;"
    glb_InsertCounter = "insert into salescounter (salesDate, counter,locationID) values (%s,%s,%s);"
    glb_UpdateSales = "update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, amount=%s, dueAmount=%s,typeOfCollection=%s, saleTime=%s, locationID=%s,dara=%s,productBarcodeID=%s where salesID=%s and salesLineID=%s and typeOfCollection=%s and saleDate=%s and locationID=%s;"
    glb_SelectSalesLineExists = "select count(*) from salesmodels where salesID=%s and salesLineID=%s and saleDate=%s and locationID=%s;"
    glb_UpdateSalesLine = "update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, amount=%s, dueAmount=%s, typeOfCollection=%s,locationID=%s,dara=%s,productBarcodeID=%s where personelID=%s and salesID=%s and salesLineID=%s and saleDate=%s and locationID=%s;"
    glb_InsertSalesLine = "insert into salesmodels (saleDate, salesID,salesLineID,personelID,amount,dueAmount,paidAmount,typeOfCollection,locationID,dara,productBarcodeID,saleTime) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    glb_SelectSales = "select  saleDate, salesID,  salesLineID, personelID, amount, productRetailPrice, productName, typeOfCollection,dara, salesmodels.productBarcodeID from salesmodels left outer join products on (salesmodels.productBarcodeID= products.productBarcodeID) where salesId=%s and typeOfCollection=%s and locationID=%s;"
    glb_SelectProductByBarcode = "select productName, productRetailPrice from products where productBarcodeID=%s;"
    glb_SelectCustomers = "Select distinct salesID from salesmodels where  saleDate=%s and typeOfCollection = -1 and locationID=%s order by salesID;"
    glb_SelectCustomersOnCashier = "Select  distinct salesID from salesmodels where  saleDate=%s and typeOfCollection = 0 and locationID=%s order by salesID;"
    glb_salesDelete = "delete from salesmodels where saleDate=%s and salesID=%s and locationID=%s;"
    glb_getBarcodeID = "SELECT barcodeID FROM packagedproductsbarcodes where recstatus=0 LIMIT 1;"
    glb_update_barcode_as_used = "update packagedproductsbarcodes set recStatus=1 where barcodeID=%s;"
    glb_insert_packedprod_items = "insert into packagedproductdetailsmodel (PackedProductID, PackagedProductLineNo, Amount, recStatus,recDate,customerID,productBarcodeID) values(%s,%s,%s,%s,%s,%s,%s);"
    glb_get_packed_details = "SELECT packagedproductdetailsmodel.productBarcodeID, amount, productName, productRetailPrice FROM packagedproductdetailsmodel left outer join  products on(packagedproductdetailsmodel.productBarcodeID=products.productBarcodeID) where packagedproductdetailsmodel.recStatus=0 and PackedProductID=%s;"
    glb_Update_Sales_As_Merged = "update salesmodels set typeOfCollection=%s where saleDate=%s and salesID=%s and locationID=%s"
    glb_package_exists = "SELECT count(PackedProductID), PackedProductID FROM packagedproductdetailsmodel where customerID = %s and DATE_FORMAT(recDate,'%%Y-%%m-%%d') = %s group by PackedProductID"
    """Connection data"""

    interface_up = False
    db_core = None

    def init(self):
        db_interface.db_core = dbCore()
        error = db_interface.db_core.connect()
        if error == "":
            db_interface.interface_up=True
        else:
            db_interface.interface_up=False

    def sql_error(self, wndHandle, errorMessage):
        db_interface.db_core.disconnect()
        db_interface.interface_up=False
        wndHandle.message_box_text.delete("1.0",END)
        wndHandle.message_box_text.insert(END,errorMessage)
        db_interface.init()

    def get_version(self):
        error = ""
        returnvalue = ""
        if (db_interface.interface_up):
            error,raws = db_interface.db_core.execsql(db_interface.glb_getversion, ())
            if error == "":
                returnvalue=raws[0][0]
        return returnvalue

    def sales_update(self, wndHandle, srcTypeOfCollection, destTypeOfCollection,saleList,locationid,base_weight):
        global glb_UpdateSales
        global glb_base_weight
        global glb_locationid
        returnvalue=False
        error=""

        if (db_interface.interface_up):
            for salesObj in saleList:
                my_date = datetime.now()
                saleTime = my_date.strftime('%Y-%m-%d %H:%M:%S.%f')
                error = db_interface.db_core.execnonesql(db_interface.glb_UpdateSales,(salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.amount, float(salesObj.retailPrice) * salesObj.amount, destTypeOfCollection, saleTime, locationid, base_weight,salesObj.productBarcodeID, salesObj.salesID, salesObj.salesLineID, srcTypeOfCollection, salesObj.saleDate, locationid,))
                if error != "":
                    break
            if error == "":
                error = db_interface.db_core.commit()
                if error == "":
                    returnvalue = True
                else:
                    db_interface.sql_error( wndHandle, error)
            else:
                db_interface.sql_error( wndHandle, error)
        else:
            db_interface.sql_error( wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def add_prepared_package(self, wndHandle, salesList):
        error = ""
        rows = ()
        returnvalue = ""
#    /* Get barcode ID for prepared package */
#   /* add products to prepered packaged table */
        if db_interface.interface_up:
            my_date = datetime.now()
            error, rows = db_interface.db_core.execsql(db_interface.glb_package_exists,(salesList[0].salesID, my_date.strftime('%Y-%m-%d')))
            if error == "":
                if len(rows)==0:
                    error, rows = db_interface.db_core.execsql(db_interface.glb_getBarcodeID,())
                    if error == "":
                        if rows is not None:
                            barcodeID = rows[0][0]
                            error = db_interface.db_core.execnonesql(db_interface.glb_update_barcode_as_used,(barcodeID,))
                            if error == "":
                                lineNo = 1
                                for salesObj in salesList:
                                    error = db_interface.db_core.execnonesql(db_interface.glb_insert_packedprod_items, (barcodeID, lineNo, salesObj.amount,"0",datetime.now(),salesObj.salesID,salesObj.productBarcodeID))
                                    lineNo = lineNo + 1
                                    if error != "":
                                        break
                                if error == "":
                                    error = db_interface.db_core.commit()
                                if error == "":
                                    returnvalue=barcodeID
                                else:
                                    db_interface.sql_error( wndHandle, error)
                            else:
                                db_interface.sql_error( wndHandle, error)
                        else:
                            db_interface.sql_error( wndHandle, "Paketli ürün için barkod kalmadı.")
                            add_to_log("add_prepared_package", "Paketli ürün için barkod kalmadı.")
                    else:
                        db_interface.sql_error( wndHandle, "Paketli ürün için barkod kalmadı veya Sql Hatası = "+ error)
                else:
                    returnvalue= rows[0][1]
        else:
          db_interface.sql_error( wndHandle, error)
        return returnvalue

    def sales_hard_delete(self, wndHandle, salesID):
        returnvalue = False
        error = ""

        if db_interface.interface_up:
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            error = db_interface.db_core.execnonesql(db_interface.glb_salesDelete,(saleDate,salesID,glb_locationid,))
            if error == "":
                error = db_interface.db_core.commit()
                if error == "":
                    returnvalue = True
                else:
                    db_interface.sql_error( wndHandle, error)
        else:
            db_interface.sql_error( wndHandle, "Veri tabanı erişim hatası. Fonksiyon : sales_hard_delete")
        return returnvalue

    def sales_save(self, wndHandle,typeOfCollection, saleList,locationid,base_weight):
        returnvalue = False
        error = ""
        rows = ()

        if db_interface.interface_up:
            i=1
            for salesObj in saleList:
                salesObj.salesLineID = i
                i=i+1
            for salesObj in saleList:
                error, rows = db_interface.db_core.execsql(db_interface.glb_SelectSalesLineExists,(salesObj.salesID,salesObj.salesLineID, salesObj.saleDate,locationid))
                if error == "":
                    if rows[0][0] > 0:
                        error = db_interface.db_core.execnonesql(db_interface.glb_UpdateSalesLine,
                                (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID,
                                salesObj.amount, float(salesObj.retailPrice) * salesObj.amount,glb_locationid,base_weight,salesObj.productBarcodeID, salesObj.personelID,
                                salesObj.salesID,salesObj.salesLineID,salesObj.saleDate,locationid))
                    else:
                        paidAmount=0.0
                        error = db_interface.db_core.execnonesql(db_interface.glb_InsertSalesLine,
                                                                 (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID,
                                                                  salesObj.personelID, salesObj.amount,float(salesObj.retailPrice) * salesObj.amount, paidAmount,
                                                                  typeOfCollection,locationid,base_weight,salesObj.productBarcodeID,datetime.now()))
                    if error != "":
                        break
                else:
                    break
            if error == "":
                error = db_interface.db_core.commit()
                if error == "":
                    returnvalue=True
                else:
                    db_interface.sql_error( wndHandle, error)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def sales_load(self, wndHandle, salesID, typeOfCollection,salesList, sales_line_id,locationid,base_weight):
        returnvalue=False
        error = ""
        rows = None

        if db_interface.interface_up:
            error,rows = db_interface.db_core.execsql(db_interface.glb_SelectSales,(salesID,typeOfCollection,locationid))
            if error == "":
                returnvalue=True
                salesList.clear()
                sales_line_id = 1
                for row in rows:
                    salesID = row[1]
                    salesObj = Sales()
                    salesObj.saleDate = row[0]
                    salesObj.salesID = row[1]
                    salesObj.salesLineID = row[2]
                    salesObj.personelID = row[3]
                    salesObj.amount = row[4]
                    salesObj.retailPrice = row[5]
                    salesObj.Name = row[6]
                    salesObj.typeOfCollection = row[7]
                    salesObj.dara=row[8]
                    salesObj.productBarcodeID=row[9]
                    base_weight = salesObj.dara
                    salesList.append(salesObj)
                    sales_line_id = sales_line_id + 1
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error( wndHandle, "Veri Tabanı bağlantı hatası")
        return returnvalue, salesList, sales_line_id, base_weight

    def sales_merge(self,wndHandle, merge_customer_no, typeOfCollection,glb_sales):
        global glb_customer_no
        global glb_sales_line_id
        global glb_customer_no
        global glb_locationid
        returnvalue=False
        error = ""
        rows = ()


        if db_interface.interface_up:
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectSales,
                                        (merge_customer_no, typeOfCollection, glb_locationid))
            if error == "":
                for row in rows:
                    salesObj = Sales()
                    salesObj.saleDate = row[0]
                    salesObj.salesID = glb_customer_no
                    salesObj.salesLineID = glb_sales_line_id
                    salesObj.personelID = row[3]
                    salesObj.amount = row[4]
                    salesObj.retailPrice = row[5]
                    salesObj.Name = row[6]
                    salesObj.typeOfCollection = row[7]
                    salesObj.productBarcodeID = row[9]
                    glb_sales.append(salesObj)
                    glb_sales_line_id = glb_sales_line_id + 1
                error = db_interface.db_core.execnonesql(db_interface.glb_Update_Sales_As_Merged,
                             (-3, salesObj.saleDate, merge_customer_no, glb_locationid))
                if error == "":
                    error = db_interface.db_core.commit()
                    if error == "":
                        returnvalue = True
                    else:
                        db_interface.sql_error( wndHandle, error)
                else:
                    db_interface.sql_error( wndHandle, error)
            else:
                db_interface.sql_error( wndHandle, error)
        else:
            db_interface.sql_error( wndHandle, "Veri Tabanı bağlantı hatası")
        return returnvalue

    def get_product_based_on_barcod(self,wndHandle, prdct_barcode, salesObj):
        global glb_cursor
        global glb_sales_line_id
        global glb_customer_no
        global glb_employees_selected
        returnvalue = False
        error = ""
        rows = ()
        if glb_employees_selected != '':
            if db_interface.interface_up:
                error, rows = db_interface.db_core.execsql(db_interface.glb_SelectProductByBarcode,(prdct_barcode,))
                if error == "":
                    if len(rows) > 0:
                        returnvalue = True
                        for row in rows:
                            salesObj.salesID = glb_customer_no
                            salesObj.salesLineID = glb_sales_line_id
                            glb_sales_line_id = glb_sales_line_id + 1
                            salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
                            salesObj.amount = 1
                            salesObj.Name = row[0]
                            salesObj.retailPrice = row[1]
                            salesObj.typeOfCollection = 0
                            salesObj.productBarcodeID=prdct_barcode
                    else:
                        db_interface.sql_error(wndHandle, prdct_barcode + " numaralı kayıt bulunamadı.")
                else:
                    db_interface.sql_error(wndHandle, error)
        else:
            self.message_box_text.insert(END, "Çalışan seçilmeden işleme devam edilemez")
        return returnvalue

    def get_served_customers(self, wndHandle, activecustomers):
        global glb_locationid
        returnvalue=False
        error = ""
        rows= ()

        if db_interface.interface_up:
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectCustomers, (saleDate, glb_locationid,))
            if error == "":
                returnvalue=True
                activecustomers.clear()
                for row in rows:
                    customer_obj = Customer()
                    customer_obj.Name = row[0]
                    activecustomers.append(customer_obj)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def get_customers_on_cashier(self,wndHandle,customerList,locationid):
        returnvalue=False
        error = ""
        rows = ()

        if db_interface.interface_up:
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectCustomersOnCashier, (saleDate, locationid,))
            if error == "":
                returnvalue = True
                customerList.clear()
                for row in rows:
                    customer_obj = Customer()
                    customer_obj.Name = row[0]
                    customerList.append(customer_obj)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def load_products(self, wndHandle, reyonID, product_names):
        returnvalue=False
        error = ""
        rows = ()
        if db_interface.interface_up:
            error, rows = db_interface.db_core.execsql(db_interface.glb_GetTeraziProducts, (reyonID,))
            if error == "":
                returnvalue = True
                product_names.clear()
                for row in rows:
                    productObj = Product()
                    productObj.teraziID = row[0]
                    productObj.Name = row[1]
                    productObj.price = float(row[2])
                    productObj.productBarcodeID=row[3]
                    product_names.append(productObj)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def wait_for_sql(self):
        while not db_interface.interface_up:
            db_interface.init()
            if db_interface.interface_up == False:
                messagebox.showinfo("Hata","Sunucu ile bağlantı kurulamadı.")
                time.sleep(2)

    def load_reyon_data(self,wndHandle, reyonlar):
        returnvalue = False
        error = ""
        rows = ()

        if db_interface.interface_up:
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectTerazi,())
            if error == "":
                returnvalue=True
                for row in rows:
                    reyonObj = Reyon()
                    reyonObj.teraziID = row[0]
                    reyonObj.ReyonName = row[1]
                    reyonlar.append(reyonObj)
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def load_employees(self, wndHandle, employees):
        returnvalue = False
        error = ""
        rows = ()

        if db_interface.interface_up:
            error, rows = db_interface.db_core.execsql(db_interface.glb_SelectEmployees,())
            if error == "":
                returnvalue = True
                for row in rows:
                    employeeObj = Employee()
                    employeeObj.Name = row[1] + " " + row[2]
                    employeeObj.personelID = row[0]
                    employees.append(employeeObj)
            else:
                db_interface.sql_error( wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue

    def get_packaged_products(self, wndHandle, barcodeID):
        returnvalue=False
        error = ""
        rows = ()
        salesList = []

        if db_interface.interface_up:
            error, rows = db_interface.db_core.execsql(db_interface.glb_get_packed_details, (barcodeID,))
            if error == "":
                returnvalue = True
                lineID = 1
                for row in rows:
                    salesObj = Sales()
                    salesObj.salesID = glb_customer_no
                    salesObj.salesLineID=lineID
                    salesObj.productBarcodeID = row[0]
                    salesObj.amount = row[1]
                    salesObj.Name = row[2]
                    salesObj.retailPrice = row[3]
                    salesObj.typeOfCollection = 0
                    salesList.append(salesObj)
                    lineID=lineID+1
            else:
                db_interface.sql_error(wndHandle, error)
        else:
            db_interface.sql_error(wndHandle, "Veri tabanı bağlantı hatası")
        return returnvalue, salesList

class load_tables:

    def __init__(self):
        global glb_scaleId
        global glb_sales_line_id
        global glb_base_weight
        global glb_customer_no
        global glb_cursor
        global glb_product_names
        global glb_reyonlar
        global glb_employees

        db_interface.wait_for_sql()
        if db_interface.load_products(self,1,glb_product_names):
            glb_scaleId = 0
            glb_sales_line_id = 1
            glb_base_weight = 0
            glb_customer_no = 0
            if db_interface.load_reyon_data(self, glb_reyonlar):
                returnvalue = db_interface.load_employees(self, glb_employees)

def print_receipt(barcod_to_be_printed):
    returnvalue = ""
#    dev = usb.core.find(idVendor=0x0416, idProduct=0x5011)
    try:
        p = Usb(0x0416, 0x5011, 0, 0x81, 0x03)
        p.cut()
#    p.charcode("Turkish")
        p._raw(b'\x1B\x07\x5B')
        p.codepage='cp857'
        p.text("\n")
        p._raw(b'\x1b\x61\x01')  # center printing
        today = datetime.now()
        p.text(today.strftime('%Y-%m-%d %H:%M:%S.%f') + '\n')
        p._raw(b'\x1b\x44\x01\x12\x19\x00\n') # set tab stops for output
        toplam=0
        for salesObj in glb_sales:
            strAmount = "{:6.3f}".format(salesObj.amount)
            strAmount = strAmount.rjust(6)
            tutar=salesObj.amount*float(salesObj.retailPrice)
            toplam=toplam+tutar
            strTutar = "{:7.2f}".format(tutar)
            strTutar = strTutar.rjust(7)
            p.text("\x09 "+salesObj.Name[0:15]+"\x09"+strAmount+"\x09"+strTutar+"\n")
        strToplam="{:7.2f}".format(toplam)
        strToplam=strToplam.rjust(7)
        p.text("\x09\x09\x09" + " ______\n")
        p.text("\x09"+" Toplam"+"\x09\x09"+strToplam)
        p.text("\n")
        with open('temp.jpeg', 'wb') as f:
            EAN13(barcod_to_be_printed, writer=ImageWriter()).write(f)
        to_be_resized=Image.open("temp.jpeg")
        newSize=(300,70)
        resized=to_be_resized.resize(newSize,resample=PIL.Image.NEAREST)
        p.image(resized, impl='bitImageColumn')
        p.text("\n"+barcod_to_be_printed)
        p.cut()
        p.close()
    except Exception as e:
        returnvalue = "Printer hatası : "+ e.msg
    return returnvalue

def maininit(gui, *args, **kwargs):
    global w, top_level, root
    w = gui
    top_level = top

def vp_start_gui():
    global w, root, top
    root = tk.Tk()
    top = MainWindow(root)
    maininit(root, top)
    root.mainloop()

class CustomerWindow(tk.Tk):
        def __init__(self, master):
            super().__init__(useTk=0)

            self.master=master
            tk.Frame.__init__(self.master)

class MainWindow(tk.Tk):

    def message_box_frame_def(self):
        global top
        self.message_box_frame.place(relx=0.0, rely=0.900, relheight=0.10, relwidth=0.994)
        self.message_box_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.message_box_frame.configure(highlightbackground="#f0f0f0", width=795)
        self.message_box_text = tk.Text(self.message_box_frame, height=1, width=80, font=("Arial Bold", 18),
                                        bg='dark red', fg="white")
        self.message_box_text.place(relx=0.0, rely=0.0, relheight=0.60, relwidth=0.994)

    def paging_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.paging_frame.place(relx=0.360, rely=0.560, relheight=0.120, relwidth=0.620)
        self.paging_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        next_button = tk.Button(self.paging_frame, text="Sonraki Sayfa")
        next_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        next_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        next_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=3,
                              wraplength=130)
        next_button.configure(command=lambda btn=next_button: self.next_product_button_clicked())
        next_button.grid(row=0, column=2)
        previous_button = tk.Button(self.paging_frame, text="Önceki Sayfa")
        previous_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        previous_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        previous_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=3,
                                  wraplength=130)
        previous_button.configure(command=lambda btn=previous_button: self.previous_product_button_clicked())
        previous_button.grid(row=0, column=0)

    def employee_frame_def(self):
        global top
        global glb_active_product_frame_content

        glb_active_product_frame_content = 0
        varfunc = self.employee_button_clicked
        self.add_frame_buttons(0, self.product_frame,glb_employees,glb_employees_page_count,varfunc)

    def customer_frame_def(self):
        global glb_active_served_customers
        global top
        global glb_active_product_frame_content

        glb_active_product_frame_content = 2
        if db_interface.get_served_customers(self, glb_active_served_customers):
            varfunc = self.customer_button_clicked
            self.add_frame_buttons(1, self.product_frame, glb_active_served_customers,glb_active_customers_page_count,varfunc)


    def call_back_customer_frame_def(self):
        global glb_customers_on_cashier
        global glb_locationid
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 3
        if db_interface.get_customers_on_cashier(self,glb_customers_on_cashier,glb_locationid):
            varfunc = self.call_back_customer_no_clicked
            self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count,varfunc)

    def display_frame_def(self):
        global top
        global root

        self.display_frame.place(relx=0.0, rely=0.0, relheight=0.100, relwidth=0.994)
        self.product_frame.configure(width=795)
        self.customer_no = tk.Text(self.display_frame, height=1, width=4, font=("Arial Bold", 25),
                                   bg='dark blue', fg="white")
        self.scale_display = tk.Text(self.display_frame, height=1, width=10, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.prdct_barcode = tk.Text(self.display_frame, height=1, width=2, font=('Arial Bold', 25))
        self.employee_text = tk.Text(self.display_frame, height=1, width=20, font=("Arial Bold", 25))
        self.scale_type.insert(END, "Kg")
        self.customer_no.insert(END, "0")
        self.employee_text.insert(END,"")
        reyon_names = []
        for index, reyonObj in enumerate(glb_reyonlar):
            reyon_names.append(reyonObj.ReyonName)
        text_font = ('Arial Bold', '22')
        root.option_add('*TCombobox*Listbox.font', text_font)
        self.select_reyon = Combobox(self.display_frame, font=text_font, values=reyon_names)
        self.select_reyon.bind("<<ComboboxSelected>>", self.checkreyon)
        self.select_reyon
        self.prdct_barcode.grid(row=0, column=0)
        self.select_reyon.grid(row=0, column=1)
        self.customer_no.grid(row=0, column=2)
        self.scale_display.grid(row=0, column=3)
        self.scale_type.grid(row=0, column=4)
        self.employee_text.grid(row=0,column=5)
        self.prdct_barcode.focus_set()
        self.prdct_barcode.bind('<Key-Return>', self.read_barcode)

    def read_barcode(self, event):
        global glb_sales
        global glb_customer_no
        global glb_sales_line_id
        global glb_employees_selected
        global root
        returnvalue = False
        salesList = None
        root.config(cursor="watch")
        root.update()
        textdata = self.prdct_barcode.get('1.0', END)
        textdata = textdata.rstrip("\n")
        textdata = textdata.lstrip("\n")
        self.prdct_barcode.delete('1.0', END)
        if textdata != "" and len(textdata) >= 12:
            product_code=int(textdata[8:12])
            if product_code >= 5600 and product_code <=5710:
                returnvalue, salesList = db_interface.get_packaged_products(self, textdata)
                if returnvalue:
                    for salesItem in salesList:
                        salesObj=Sales()
                        salesObj.salesID=glb_customer_no
                        salesObj.salesLineID = glb_sales_line_id
                        glb_sales_line_id = glb_sales_line_id + 1
                        salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
                        salesObj.amount = salesItem.amount
                        salesObj.Name = salesItem.Name
                        salesObj.retailPrice = salesItem.retailPrice
                        salesObj.typeOfCollection = 0
                        salesObj.productBarcodeID=salesItem.productBarcodeID
                        salesObj.productID=salesItem.productID
                        glb_sales.append(salesObj)
            else:
                salesObj = Sales()
                if db_interface.get_product_based_on_barcod(self, textdata, salesObj):
                    glb_sales.append(salesObj)
            self.update_products_sold()
            if glb_customer_window == 1:
                self.update_products_sold_for_customer()
        root.config(cursor="")


    def add_frame_buttons(self, active_served_customers, frame, btn_list, page_count, func):
        global glb_screensize
        global glb_merge_customer_flag

        if glb_screensize == 800:
            buttonwidth=19
            buttonheight=2
            row_size, col_size = 4, 2
            btn_font = "-family {Segoe UI} -size 12 -weight bold -slant " \
                     "roman -underline 0 -overstrike 0"
        else:
            buttonwidth=24
            buttonheight=2
            row_size, col_size = 5, 2
            btn_font = "-family {Segoe UI} -size 16 -weight bold -slant " \
                     "roman -underline 0 -overstrike 0"

        for child in frame.winfo_children():  # Clear frame contents whatever it is
            child.destroy()
        lower_cnt = page_count * row_size * col_size  # calculate lower bound in the btn_list
        while lower_cnt > len(btn_list):  # if lower bound is more than list size adjust it
            page_count = page_count - 1
            lower_cnt = page_count * row_size * col_size
        upper_cnt = lower_cnt + row_size * col_size  # calculate upper bound in the list
        if upper_cnt > len(btn_list):  # if upper bound more than list size adjust it
            upper_cnt = len(btn_list)
        btn_no = 0
        while lower_cnt < upper_cnt:
            obj = btn_list[lower_cnt]
            button = tk.Button(frame, text=obj.Name)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=buttonwidth, height=buttonheight,
                             wraplength=400)
            button.configure(command=lambda btn=button: func(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
            btn_no = btn_no + 1
            lower_cnt = lower_cnt + 1
        if active_served_customers:
            if (glb_merge_customer_flag == None):
                btn_no = btn_no + 1
                button = tk.Button(self.product_frame, text="Yeni Müşteri")
                button.configure(command=lambda btn=button: self.new_customer_clicked())
                button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                                 disabledforeground="#a3a3a3")
                button.configure(font=btn_font, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                                 pady="0", width=buttonwidth, height=buttonheight)
                button.configure(wraplength=200)
                button.grid(row=int(btn_no / col_size), column=btn_no % col_size)

        return page_count

    def product_frame_def(self):
        global top
        global glb_active_product_frame_content
        global glb_product_page_count
        self.product_frame.place(relx=0.360, rely=0.110, relheight=0.440, relwidth=0.620)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        glb_active_product_frame_content = 1
        varfunc = self.product_button_clicked
        glb_product_page_count = self.add_frame_buttons(0,self.product_frame, glb_product_names, glb_product_page_count, varfunc)

    def productssold_frame_def(self):
        global top
        if glb_screensize==800:
            sum_font = "-family {Segoe UI} -size 8 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
            entry_products_font = "-family {Segoe UI} -size 8 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        else:
            sum_font = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
            entry_products_font = "-family {Segoe UI} -size 10 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.products_sold_frame.place(relx=0.0, rely=0.110, relheight=0.550, relwidth=0.350)
        self.products_sold_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9",
                                           highlightbackground="#d9d9d9")
        self.products_sold_frame.configure(highlightcolor="black", width=155)
        self.entry_products = tk.Text(self.products_sold_frame)
        self.entry_products.place(relx=0.010, rely=0.02, relheight=0.84, relwidth=0.650)
        self.entry_products.configure(font=entry_products_font)
        self.entry_products.configure(takefocus="")
        self.entry_amount_sold=tk.Text(self.products_sold_frame)
        self.entry_amount_sold.tag_configure("right",justify=RIGHT)
        self.entry_amount_sold.tag_add("right",1.0,"end")
        self.entry_amount_sold.place(relx=0.650, rely=0.02, relheight=0.84, relwidth=0.160)
        self.entry_amount_sold.configure(font=entry_products_font, takefocus="")

        self.entry_calculatedtotal = tk.Text(self.products_sold_frame)
        self.entry_calculatedtotal.tag_configure("right",justify=RIGHT)
        self.entry_calculatedtotal.tag_add("right",1.0,"end")
        self.entry_calculatedtotal.place(relx=0.810, rely=0.02, relheight=0.84, relwidth=0.170)
        self.entry_calculatedtotal.configure(font=entry_products_font, takefocus="")
        self.label_sum = tk.Label(self.products_sold_frame)
        self.label_sum.place(relx=0.040, rely=0.88, relheight=0.10, relwidth=0.300)
        # self.label_sum.configure(background="#d9d9d9")
        self.label_sum.configure(disabledforeground="#a3a3a3")
        self.label_sum.configure(font=sum_font)
        self.label_sum.configure(foreground="#000000")
        self.label_sum.configure(text='''Toplam''')
        self.entry_sum = tk.Text(self.products_sold_frame, height=1, width=80, font=sum_font)
        self.entry_sum.tag_configure("right",justify=RIGHT)
        self.entry_sum.tag_add("right",1.0,"end")
        self.entry_sum.place(relx=0.790, rely=0.88, relheight=0.10, relwidth=0.190)

    def set_button_configuration(self,button,btn_font,cmd,txt):
        button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        button.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000",highlightbackground="#d9d9d9", highlightcolor="black")
        button.configure(pady="0", text = txt, command = cmd)

    def functions_frame_def(self):
        global top
        global glb_screensize

        buttons_x_start = 25
        buttons_x_start = 25
        buttons_x_distance = 30
        buttons_y_start = 10
        buttons_y_distance = 10
        if glb_screensize==800:
            buttons_height = 38
            buttons_width = 150
            buttons_height = 38
            buttons_width = 150
            buttons_x_start = 5
            buttons_x_distance = 3
            buttons_y_start = 3
            buttons_y_distance = 3
            btn_font = "-family {Segoe UI} -size 11 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        else:
            buttons_height = 50
            buttons_width = 220
            buttons_x_start = 15
            buttons_x_distance = 30
            buttons_y_start =5
            buttons_y_distance = 5
            btn_font = "-family {Segoe UI} -size 15 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.functions_frame.place(relx=0.001, rely=0.700, relheight=0.200, relwidth=0.980)
        self.functions_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.functions_frame.configure(highlightbackground="#f0f0f0")
        # Dara button definition
        self.btn_dara = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_dara,btn_font,lambda btn=self.btn_dara: self.btn_dara_clicked(),"Dara")
        buttons_x_count=0
        buttons_y_count =0
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_dara.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        #change user button definition
        self.btn_changeuser = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_changeuser,btn_font,lambda btn=self.btn_changeuser: self.btn_change_user_clicked(),"Çalışan Değiştir")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_changeuser.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        # call back customer button definition
        self.btn_call_back_customer = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_call_back_customer,btn_font,lambda btn=self.btn_call_back_customer: self.call_back_customer_clicked(),"Müşteri Geri Çağır")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_call_back_customer.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        #cancel sale button definition
        self.btn_cancelsale = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_cancelsale,btn_font,lambda btn=self.btn_cancelsale: self.btn_cancelsale_clicked(),"Satış İptal")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_cancelsale.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        # add packed product button definition
        self.btn_addpackedproduct = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_addpackedproduct,btn_font,lambda btn=self.btn_addpackedproduct: self.btn_addpackedproduct_clicked(),"Tepsi Ekle")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_addpackedproduct.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        buttons_y_count=buttons_y_count+1
        buttons_x_count=0

        self.btn_cleardara = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_cleardara,btn_font,lambda btn=self.btn_cleardara: self.btn_cleardara_clicked(),"Darayı Temizle")
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_cleardara.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        self.btn_savesale = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_savesale,btn_font,lambda btn=self.btn_savesale: self.btn_savesale_clicked(),"Satışı Kaydet")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_savesale.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        self.btn_sendcashier = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_sendcashier,btn_font,lambda btn=self.btn_sendcashier: self.btn_send_cashier_clicked(),"Kasaya Gönder")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_sendcashier.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        self.btn_clearlasttransaction = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_clearlasttransaction,btn_font,lambda btn=self.btn_clearlasttransaction: self.btn_clearlasttransaction_clicked(),"Son İşlemi Sil")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_clearlasttransaction.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

        self.btn_mergesales = tk.Button(self.functions_frame)
        self.set_button_configuration(self.btn_mergesales,btn_font,lambda btn=self.btn_mergesales: self.btn_mergesales_clicked(),"Satış Birleştir")
        buttons_x_count=buttons_x_count+1
        xpos=buttons_x_start+buttons_x_count*buttons_x_distance+buttons_x_count*buttons_width
        ypos=buttons_y_start + buttons_y_count*buttons_y_distance+buttons_y_count*buttons_height
        self.btn_mergesales.place(x=xpos, y=ypos, height=buttons_height, width=buttons_width)

    def btn_addpackedproduct_clicked(self):
        error =""
        barcodeID=db_interface.add_prepared_package(self,glb_sales)
        if barcodeID != "":
            error=print_receipt(barcodeID)
            if error == "":
                glb_sales.clear()
                self.update_products_sold()
                if glb_customer_window == 1:
                    self.update_products_sold_for_customer()
                self.btn_cleardara_clicked()
                self.new_customer_clicked()
            else:
                self.message_box_text.delete("1.0", END)
                self.message_box_text.insert(END,error)

    def next_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content
        global root

        root.config(cursor="watch")
        root.update()
        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            glb_employees_page_count = glb_employees_page_count + 1
            varfunc = self.employee_button_clicked
            glb_employees_page_count = self.add_frame_buttons(0, self.product_frame,glb_employees,glb_employees_page_count, varfunc)
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            glb_product_page_count = glb_product_page_count + 1
            varfunc = self.product_button_clicked
            glb_product_page_count = self.add_frame_buttons(0, self.product_frame,glb_product_names,glb_product_page_count, varfunc)
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
             glb_active_customers_page_count = glb_active_customers_page_count + 1
             varfunc = self.customer_button_clicked
             glb_active_customers_page_count = self.add_frame_buttons(1, self.product_frame,glb_active_served_customers,glb_active_customers_page_count, varfunc)
        else:  # Middle frame for callback customers
            glb_callback_customers_page_count = glb_callback_customers_page_count + 1
            varfunc = self.call_back_customer_no_clicked
            glb_callback_customers_page_count = self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count, varfunc)
        root.config(cursor="")

    def previous_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content
        global root

        root.config(cursor="watch")
        root.update()
        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            if glb_employees_page_count > 0:
                glb_employees_page_count = glb_employees_page_count - 1
            varfunc = self.employee_button_clicked
            glb_employees_page_count = self.add_frame_buttons(0, self.product_frame, glb_employees, glb_employees_page_count, varfunc)
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            if glb_product_page_count > 0:
                glb_product_page_count = glb_product_page_count - 1
            varfunc = self.product_button_clicked
            glb_product_page_count = self.add_frame_buttons(0, self.product_frame,glb_product_names,glb_product_page_count, varfunc)
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
            if glb_active_customers_page_count > 0:
                glb_active_customers_page_count = glb_active_customers_page_count -1
            varfunc = self.customer_button_clicked
            glb_active_customers_page_count = self.add_frame_buttons(1, self.product_frame,glb_active_served_customers,glb_active_customers_page_count, varfunc)
        else:  # Middle frame for callback customers
            if glb_callback_customers_page_count > 0:
               glb_callback_customers_page_count = glb_callback_customers_page_count - 1
            varfunc = self.call_back_customer_no_clicked
            glb_callback_customers_page_count = self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count, varfunc)
        root.config(cursor="")

    def customer_button_clicked(self, btn):
        global glb_customer_no
        global glb_locationid
        global glb_base_weight
        global glb_sales_line_id
        global glb_sales
        global root
        global glb_merge_customer_flag
        noerror=False

        root.config(cursor="watch")
        root.update()
        if (glb_merge_customer_flag == MERGE_CUSTOMERS):
            glb_merge_customer_flag=None
            merge_customer_no = btn.cget("text")
            noerror=db_interface.sales_merge(self, merge_customer_no,-1,glb_sales)
        else:
            glb_customer_no = btn.cget("text")
            self.customer_no.delete('1.0', END)
            self.customer_no.insert(END, glb_customer_no)
            noerror,glb_sales, glb_sales_line_id, glb_base_weight =db_interface.sales_load(self, glb_customer_no, -1,glb_sales,glb_sales_line_id, glb_locationid, glb_base_weight)
        if noerror==True:
            self.product_frame_def()
            self.update_products_sold()
            if glb_customer_window==1:
                self.update_products_sold_for_customer()
        root.config(cursor="")

    def btn_send_cashier_clicked(self):
        global glb_customer_no
        global glb_sales_line_id
        global glb_webHost
        global root

        root.config(cursor="watch")
        root.update()
        if (db_interface.sales_hard_delete(self, glb_customer_no)):
            if db_interface.sales_save(self, 0, glb_sales,glb_locationid,glb_base_weight):
                glb_sales.clear()
                self.update_products_sold()
                if glb_customer_window==1:
                    self.update_products_sold_for_customer()
                glb_customer_no = 0
                glb_sales_line_id = 1
                self.customer_no.delete('1.0', END)
                self.customer_no.insert(END, "0")
                try:
                    resp = requests.get(glb_webHost+"/api/DataRefresh",verify=False)
                except requests.exceptions.RequestException as e:
                    msg=e.args[0].args[0]
                    add_to_log("sendToCahsier","SignalRErr :"+msg)
                self.btn_cleardara_clicked()
                self.new_customer_clicked()
        root.config(cursor="")

    def btn_change_user_clicked(self):
        global top
        global glb_employees_selected
        global glb_customer_no
        global root
        global glb_serialthread
        global glb_merge_customer_flag

        root.config(cursor="watch")
        root.update()
        if glb_serialthread.is_alive() == False:
            glb_serialthread = threading.Thread(target=get_data,
                                                args=(self, self.scale_display,))
            glb_serialthread.daemon = True
            glb_serialthread.start()
        glb_sales.clear()
        glb_customer_no = 0
        self.update_products_sold()
        if glb_customer_window ==1:
            self.update_products_sold_for_customer()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.employee_frame_def()
        glb_employees_selected = ""
        glb_merge_customer_flag=None
        root.config(cursor="")

    def btn_mergesales_clicked(self):
        global glb_merge_customer_flag

        root.config(cursor="watch")
        root.update()
        glb_merge_customer_flag = MERGE_CUSTOMERS
        self.customer_frame_def()
        root.config(cursor="")

    def call_back_customer_no_clicked(self, btn):
        global root
        global glb_customer_no
        global glb_locationid
        global glb_base_weight
        global glb_webHost
        global glb_sales_line_id
        global glb_sales
        returnvalue = False

        root.config(cursor="watch")
        root.update()
        glb_customer_no = btn.cget("text")
        returnvalue, glb_sales, glb_sales_line_id, glb_base_weight = db_interface.sales_load(self, glb_customer_no, 0,glb_sales,glb_sales_line_id, glb_locationid, glb_base_weight)
        if (returnvalue):
            if db_interface.sales_update(self, 0, -1, glb_sales,glb_locationid,glb_base_weight):
                self.customer_no.delete('1.0', END)
                self.customer_no.insert(END, glb_customer_no)
                self.update_products_sold()
                if glb_customer_window==1:
                    self.update_products_sold_for_customer()
                self.product_frame_def()
                resp = requests.get(glb_webHost+"/api/DataRefresh",verify=False)
        root.config(cursor="")

    def call_back_customer_clicked(self):
        global root

        root.config(cursor="watch")
        root.update()
        self.call_back_customer_frame_def()
        root.config(cursor="")

    def new_customer_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        global root

        root.config(cursor="watch")
        root.update()
        salescounterobj = SalesCounter()
        returnvalue, temp = salescounterobj.get_counter(self)
        if temp != -1:
            self.message_box_text.delete("1.0", END)
            glb_sales.clear()
            glb_customer_no=temp
            self.customer_no.delete('1.0', END)
            self.customer_no.insert(END, glb_customer_no)
            glb_sales_line_id = 1
            self.product_frame_def()
        root.config(cursor="")

    def btn_cancelsale_clicked(self):
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        global glb_locationid
        global glb_base_weight
        global root

        root.config(cursor="watch")
        root.update()
        if db_interface.sales_hard_delete(self, glb_customer_no):
            if db_interface.sales_save(self, -2,glb_sales,glb_locationid,glb_base_weight):
                self.message_box_text.delete("1.0", END)
                glb_sales.clear()
                self.update_products_sold()
                self.customer_no.delete('1.0', END)
                self.customer_no.insert(END, "0")
                glb_sales_line_id = 1
                glb_customer_no = 0
                self.new_customer_clicked()
                self.btn_cleardara_clicked()
        root.config(cursor="")

    def btn_savesale_clicked(self):
        global glb_sales_line_id
        global glb_locationid
        global glb_base_wight
        global glb_customer_no
        global root

        root.config(cursor="watch")
        root.update()
        if db_interface.sales_hard_delete(self, glb_customer_no):
            if db_interface.sales_save(self, -1,glb_sales,glb_locationid, glb_base_weight):
#        self.message_box_text.delete("1.0", END)
                glb_sales.clear()
                self.update_products_sold()
                self.customer_no.delete('1.0', END)
                self.customer_no.insert(END, "0")
                glb_sales_line_id = 1
                self.btn_change_user_clicked()
        root.config(cursor="")

    def btn_dara_clicked(self):
        global glb_base_weight
        global root

        root.config(cursor="watch")
        root.update()
        glb_base_weight = glb_base_weight + float(self.scale_display.get("1.0", END).strip("\n"))
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, "0.000".rjust(13))
        root.config(cursor="")

    def btn_cleardara_clicked(self):
        global glb_base_weight
        global root
        global glb_filter_data

        root.config(cursor="watch")
        root.update()
        glb_base_weight = 0
        if (glb_filter_data != '' ):
            floatval = float(glb_filter_data) - glb_base_weight
        else:
            floatval=0
        mydata = "{:10.3f}".format(floatval)
        mydata = mydata.rjust(13)
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, mydata)
        root.config(cursor="")

    def btn_clearlasttransaction_clicked(self):
        global glb_sales_line_id
        global root

        root.config(cursor="watch")
        root.update()
        if len(glb_sales) > 0:
            glb_sales.pop(-1)
            glb_sales_line_id = glb_sales_line_id -1
            self.update_products_sold()
            if glb_customer_window==1:
                self.update_products_sold_for_customer()
        root.config(cursor="")

    def checkreyon(self, event: object):
        global glb_scaleId
        global glb_employees_selected
        global root

        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        if glb_employees_selected != "":
            tt = self.select_reyon.get()
            glb_scaleId = self.select_reyon.current()
            teraziID = [x.teraziID for x in glb_reyonlar if x.ReyonName == tt][0]
            if db_interface.load_products(self, teraziID,glb_product_names):
                for child in self.product_frame.winfo_children():
                    child.destroy()
                self.product_frame_def()
                self.functions_frame_def()
                self.select_reyon.current(glb_scaleId)
                self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Çalışan seçilmeden işleme devam edilemez")
        root.config(cursor="")

    def employee_button_clicked(self, btn):
        global glb_scaleId
        global glb_employees_selected
        global root
        global glb_location_id
        global glb_base_weight
        global glb_sales_line_id
        global glb_sales
        global glb_customer_no
        returnvalue = False

        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        glb_scaleId = self.select_reyon.current()
        if glb_scaleId != -1:
            glb_employees_selected = btn.cget("text")
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.display_frame.grid(row=0, column=0, columnspan=2)
            self.products_sold_frame.grid(row=1, column=0, rowspan=2)
            self.product_frame.grid(row=1, column=1)
            self.paging_frame.grid(row=2, column=1)
            self.functions_frame.grid(row=3, column=0, columnspan=2)
            self.message_box_frame.grid(row=4, column=0, columnspan=2)
            self.product_frame_def()
            self.functions_frame_def()
            self.employee_frame_def()
            self.paging_frame_def()
            self.productssold_frame_def()
            self.message_box_frame_def()
            tt = self.select_reyon.get()
            teraziID = [x.teraziID for x in glb_reyonlar if x.ReyonName == tt][0]
            if db_interface.load_products(self, teraziID,glb_product_names):
                for child in self.product_frame.winfo_children():
                    child.destroy()
                self.customer_frame_def()
                self.functions_frame_def()
                self.select_reyon.current(glb_scaleId)
                returnvalue, glb_sales, glb_sales_line_id, glb_base_weight = db_interface.sales_load(self,glb_customer_no, -1,glb_sales,glb_sales_line_id,glb_locationid,glb_base_weight)
                if returnvalue:
                    self.update_products_sold()
                    self.customer_no.delete('1.0', END)
                    self.customer_no.insert(END, glb_customer_no)
                    self.employee_text.delete('1.0', END)
                    self.employee_text.tag_configure('right',justify='right')
                    self.employee_text.insert(END,glb_employees_selected,'right')
                    self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Reyon Seçimini Yapmadan Personel Seçimi Yapılamaz")
        root.config(cursor="")

    def update_products_sold(self):
        self.entry_products.delete("1.0", END)
        self.entry_amount_sold.delete("1.0",END)
        self.entry_calculatedtotal.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.entry_products.insert(END, " "+salesObj.Name + "\n")
            strAmount="{:.3f}\n".format(salesObj.amount).rjust(6, ' ')
            self.entry_amount_sold.insert(END,strAmount,"right")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.entry_calculatedtotal.insert(END, myData,"right")
        self.entry_sum.delete("1.0", END)
        self.entry_sum.insert(END, "{:5.2f}".format(sum_calculated_price).rjust(8, ' '),"right")

    def update_products_sold_for_customer(self):
        self.cust_window.products_sold.delete("1.0", END)
        self.cust_window.products_sold_amount.delete("1.0", END)
        self.cust_window.products_sold_price.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.cust_window.products_sold.insert(END, salesObj.Name + "\n")
            self.cust_window.products_sold_amount.insert(END, "{:.3f}\n".format(salesObj.amount).rjust(8, ' '), "right")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.cust_window.products_sold_price.insert(END, myData, "right")
        self.cust_window.products_sold_total.delete("1.0", END)
        self.cust_window.products_sold_total.insert(END, "{:.2f}".format(sum_calculated_price).rjust(8, ' '), "right")

    def product_button_clicked(self, btn):
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        global glb_filter_data
        global glb_serialthread

        if (glb_customer_no != 0):
            if glb_serialthread.is_alive() == False:
                if glb_data_entry == 0:
                    glb_serialthread = threading.Thread(target=get_data,
                                                    args=(self, self.scale_display,))
                    glb_serialthread.daemon = True
                    glb_serialthread.start()
                    time.sleep(2)
            salesObj = Sales()
            salesObj.Name = btn.cget("text")
            salesObj.salesID = glb_customer_no
            salesObj.salesLineID = glb_sales_line_id
            glb_sales_line_id = glb_sales_line_id + 1
            salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
            salesObj.productBarcodeID=[x.productBarcodeID for x in glb_product_names if x.Name == salesObj.Name][0]
            productCode = int(salesObj.productBarcodeID[8:12])
            """if productBarcodeID is 9999 then amount becomes 1. this is used for products where barcode ID does not exists and price does not depend on weight"""
            amountTxt=""
            if productCode >= 9900 and productCode <=9928:
                amountTxt="1.0"
            else:
                amountTxt = self.scale_display.get("1.0", END).strip("\n")
                glb_filter_data=amountTxt
            if len(amountTxt) > 0:
                salesObj.amount = float(amountTxt)
            else:
                self.message_box_text.insert(END, "Miktar bilgisi hatalı")
                return
            salesObj.retailPrice = [x.price for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.typeOfCollection = 0
            glb_sales.append(salesObj)
            self.update_products_sold()
            if glb_customer_window==1:
                self.update_products_sold_for_customer()
        else:
            self.message_box_text.insert(END, "Yeni Müşteri Seçilmeden Ürün Seçimi Yapılamaz")

    def __init__(self, top):
        super().__init__(useTk=0)
        global glb_screensize
        global glb_serial_object
        global glb_serialthread

        glb_screensize=top.winfo_screenwidth()
        w, h =  top.winfo_screenwidth()/2, root.winfo_screenheight()
        top.geometry("%dx%d+0+0" % (w, h))
        top.attributes("-fullscreen", FALSE)
        # top.geometry("800x480+1571+152")
        top.title("Terazi Ara Yüzü "+"Versiyon:"+glb_version_str)
        top.configure(background="#d9d9d9")
        load_tables()
        """Create frames"""
        """self.master=top"""
        self.display_frame = tk.Frame(top)
        self.products_sold_frame = tk.Frame(top)
        self.product_frame = tk.Frame(top)
        self.paging_frame = tk.Frame(top)
        self.functions_frame = tk.Frame(top)
        self.message_box_frame = tk.Frame(top)
        """define screen orientation"""
        self.display_frame.grid(row=0, column=0, columnspan=2)
        self.products_sold_frame.grid(row=1, column=0, rowspan=2)
        self.product_frame.grid(row=1, column=1)
        self.paging_frame.grid(row=2, column=1)
        self.functions_frame.grid(row=3, column=0, columnspan=2)
        self.message_box_frame.grid(row=4, column=0, columnspan=2)
        """define frame contents, except product frame glb_employees will be displayed in product frame"""
        self.product_frame_def()
        self.display_frame_def()
        self.functions_frame_def()
        self.employee_frame_def()
        self.paging_frame_def()
        self.productssold_frame_def()
        self.message_box_frame_def()
        """"Customer view window definition """
        if glb_customer_window==1:
            self.cust_window = tk.Toplevel(self.master)
            self.cust_window.geometry("%dx%d+1200+0" % (w, h))
            self.cust_window.attributes("-fullscreen", True)
            self.cust_window.title("Müşteri Bilgi Ekranı")
            customer_window_def(self.cust_window)
        glb_serialthread = threading.Thread(target=get_data,
                                      args=(self, self.scale_display,))
        glb_serialthread.daemon = True
        glb_serialthread.start()

def customer_window_def(CustomerWindow):
        font18 = "-family {Segoe UI} -size 18 -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"

        CustomerWindow.company_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.company_label.place(relx=0.40, rely=0.0, relheight=0.05, relwidth=0.200)
        CustomerWindow.company_label.config(text='''G Ü L S E V EN''', fg='dark red')
        CustomerWindow.products_sold_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_label.place(relx=0.010, rely=0.05, relheight=0.1, relwidth=0.700)
        CustomerWindow.products_sold_label.config(text=''' Ürün''', anchor=W, bg='dark red', fg='white')
        CustomerWindow.products_sold = tk.Text(CustomerWindow, height=2, width=30)
        CustomerWindow.products_sold.place(relx=0.010, rely=0.16, relheight=0.70, relwidth=0.700)
        CustomerWindow.products_sold.configure(font=font18)
        CustomerWindow.products_sold.configure(takefocus="")
        CustomerWindow.products_sold_amount_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_amount_label.place(relx=0.720, rely=0.05, relheight=0.1, relwidth=0.10)
        CustomerWindow.products_sold_amount_label.config(text='''Miktar ''', anchor=E, bg='dark red', fg='white')
        CustomerWindow.products_sold_amount = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_amount.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_amount.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_amount.place(relx=0.720, rely=0.16, relheight=0.70, relwidth=0.10)
        CustomerWindow.products_sold_amount.configure(font=font18)
        CustomerWindow.products_sold_price_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_price_label.place(relx=0.830, rely=0.05, relheight=0.1, relwidth=0.15)
        CustomerWindow.products_sold_price_label.config(text='''Tutar ''', anchor=E, bg='dark red', fg='white')
        CustomerWindow.products_sold_price = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_price.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_price.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_price.place(relx=0.830, rely=0.16, relheight=0.70, relwidth=0.15)
        CustomerWindow.products_sold_price.configure(font=font18)
        CustomerWindow.products_sold_total_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_total_label.place(relx=0.720, rely=0.87, relheight=0.1, relwidth=0.10)
        CustomerWindow.products_sold_total_label.config(text=''' TOPLAM ''', anchor=NW, bg='dark red', fg='white')
        CustomerWindow.products_sold_total = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_total.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_total.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_total.place(relx=0.830, rely=0.87, relheight=0.10, relwidth=0.15)
        CustomerWindow.products_sold_total.configure(font=font18, bg='dark red', fg='white')

def connect(self, baud, myport ):
    global glb_serial_object

    try:
            glb_serial_object = serial.Serial(port=myport, baudrate=baud)
    except serial.SerialException as msg:
           messagebox.showinfo("Hata Mesajı", "Terazi ile Bağlantı kurulamadı. Terazinin açık ve bağlı olduğunu kontrol edip tekrar başlatın.")
           add_to_log("Connect", "Seri Port Hatası "+myport)
           return False
    return True

def checkiffloat(strval):
    x=['0','1','2','3','4','5','6','7','8','9','.',]
    i=0
    numericval=False
    while i<len(strval) and strval[i] in x:
        i=i+1
    if i == len(strval):
        numericval=True
    return numericval

def get_data(self, scale_display):
    """This function serves the purpose of collecting data from the serial object and storing
    the filtered data into a global variable.

    The function has been put into a thread since the serial event is a blocking function.
    """
    global glb_serial_object
    global glb_filter_data
    glb_filter_data = ""
    res = 0
    i=0
    while not res and i< 5:
        try:
            if glb_data_entry == 0:
                if sys.platform == "win32":
                    res=connect(self, 'COM'+str(i), 9600)
                else:
                    res=connect(self, 9600, '/dev/tty'+'USB'+str(i))
        except pymysql.Error as err:
                pass
        i=i+1
    if res:
        while (1):
            try:
                serial_data = str(glb_serial_object.readline(), 'utf-8')
                serial_data = serial_data.rstrip('\r')
                serial_data = serial_data.rstrip('\n')
                if (serial_data[0:1] == '+') and (serial_data.find("kg",1,len(serial_data))):
                    glb_filter_data = serial_data[1:serial_data.index("kg")]
                    scale_display.insert(END, '0.000'.rjust(13))
                    scale_display.delete(1.0, END)
                    floatval=0
                    while not checkiffloat(glb_filter_data) and len(glb_filter_data) > 1:
                       glb_filter_data = glb_filter_data[1:len(glb_filter_data)]
                    if checkiffloat(glb_filter_data):
                       floatval = float(glb_filter_data) - glb_base_weight
                    else:
                       floatval=0-glb_base_weight
                    mydata = "{:10.3f}".format(floatval)
                    mydata = mydata.rjust(13)
                    scale_display.insert(END, mydata)
                    print(glb_filter_data)
                else:
                   pass
            except (NameError, TypeError,UnicodeDecodeError,ValueError):
                error_message = traceback.format_exc()
                add_to_log("Get data",error_message)
                pass

def getopts(argv):
   opts = {}
   while argv:
      if argv[0][0] == '-': # find "-name value" pairs
         opts[argv[0]] = argv[1] # dict key is "-name" arg
         argv = argv[2:]
      else:
         argv = argv[1:]
   return opts

if __name__ == '__main__':
    from sys import argv
    myargs = getopts(argv)
    glb_data_entry=0
    if ("-dataentry" in myargs.keys() ):
        glb_data_entry=int(myargs["-dataentry"])
    if ("-customerwindow" in myargs.keys()):
        glb_customer_window=int(myargs["-customerwindow"])
    if ("-location" in myargs.keys() ):
        glb_locationid = myargs["-location"]
    db_interface = db_interface()
    db_interface.wait_for_sql()
    if (glb_version_str == db_interface.get_version()):
        vp_start_gui()
    else:
        if sys.platform == "win32":
            logpath = "c:\\users\\hakan\\PycharmProjects\\terazi\\"
        else:
            logpath = "/home/pi/PycharmProjects/terazi/"
        print("Yeni Versiyon Üretilmiş. Yeni versiyon indiriliyor lütfen bekleyiniz. ")
        command=sys.executable+" "+logpath + "ftpget.py"
        i = 0
        while i<len(argv):
            command=command+ " " +argv[i]
            i = i+1
        os.system(command)






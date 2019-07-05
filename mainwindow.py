import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import pyodbc
import threading
import serial
import datetime

glb_customer_no = 0
top = None
glb_product_names = []
glb_reyons = []
glb_employees = []
glb_sales = []
glb_connection_str = 'DSN=GULSEVEN;UID=hakan;PWD=ZXCvbn123'
"""glb_connection_str = 'DRIVER={FreeTDS};SERVER=192.168.1.106;PORT=51012;DATABASE=GULSEVEN;UID=hakan;PWD=ZXCvbn123;TDS_Version=7.2'"""
glb_scaleId = 0
glb_employeeselected = ''
glb_sales_line_id = 1
glb_base_weight = 0
glb_product_page = 0

class Product(object):
    def __init__(self, productID=None, productName=None, price=None, teraziID=None):
        self.productID = productID
        self.productName = productName
        self.price = price
        self.teraziID = teraziID


class Reyon(object):
    def __init__(self, teraziID=None, ReyonName=None):
        self.teraziID = teraziID
        self.ReyonName = ReyonName


class Employee(object):
    def __init__(self, personelID=None, Persname=None):
        self.personelID = personelID
        self.Persname = Persname


class SalesCounter(object):
    def __init__(self, salesDate=None, counter=None):
        self.salesDate = salesDate
        self.counter = 0

    def getcounter(self):
        conn = pyodbc.connect(glb_connection_str)
        cursor = conn.cursor()
        mydate = datetime.date.today()
        cursor.execute("select counter from salesCounter where salesDate=?", mydate.strftime('%Y-%m-%d'))
        number_of_rows = 0
        for row in cursor:
            number_of_rows = number_of_rows + 1
            self.counter = row[0] + 1
        if number_of_rows > 0:
            cursor.execute("Update salesCounter set counter=? where salesDate=?", self.counter, mydate.strftime('%Y-%m-%d'))
        else:
            self.counter = 1
            cursor.execute("Insert into salesCounter (salesDate, counter) values (?,?)", mydate.strftime('%Y-%m-%d'),
                           self.counter)
        cursor.commit()
        cursor.close()
        return self.counter


class Sales(object):
    def __init__(self, salesID=None, salesLineID=None, personelID=None, productID=None, productName=None,
                 retailPrice=None, amount=None, typeOfCollection=None):
        mydate=datetime.date.today()
        self.saleDate = mydate.strftime('%Y-%m-%d')
        self.salesID = salesID
        self.salesLineID = salesLineID
        self.personelID = personelID
        self.productID = productID
        self.productName = productName
        self.retailPrice = retailPrice
        self.amount = amount
        self.typeOfCollection = typeOfCollection

def sales_update(typeOfCollection):
    conn = pyodbc.connect(glb_connection_str)
    cursor = conn.cursor()
    for salesObj in glb_sales:
        cursor.execute(
            "update dbo.SalesModels set saleDate=?, salesID=?,  salesLineID=?, personelID=?, productID=?, amount=?, typeOfCollection=? "
            "where personelID=? and salesID=? and salesLineID=? and typeOfCollection=?"
            , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
            salesObj.amount, typeOfCollection, salesObj.personelID, salesObj.salesID,salesObj.salesLineID, "-1")
    conn.commit()
    cursor.close()

def sales_save(typeOfCollection):
    conn = pyodbc.connect(glb_connection_str)
    cursor = conn.cursor()
    for salesObj in glb_sales:
        cursor.execute("select count(*) from dbo.SalesModels where personelID=? and typeOfCollection=? and salesLineID=?", salesObj.personelID, -1, salesObj.salesLineID)
        number_of_rows = cursor.fetchone()[0]
        if number_of_rows > 0:
            cursor.execute(
                "update dbo.SalesModels set saleDate=?, salesID=?,  salesLineID=?, personelID=?, productID=?, amount=?,"
                "typeOfCollection=? where personelID=? and typeOfCollection=? and salesID=? and salesLineID=?"
                , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
                salesObj.amount, typeOfCollection, salesObj.personelID, -1, salesObj.salesID, salesObj.salesLineID)
        else:
            cursor.execute(
                "insert into dbo.SalesModels (saleDate, salesID,  salesLineID, personelID, productID, amount, typeOfCollection) values (?,?,?,?,?,?,?)"
                , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
                salesObj.amount, typeOfCollection)
    conn.commit()
    cursor.close()

def sales_load(typeOfCollection):
    global glb_customer_no
    global glb_sales_line_id
    conn = pyodbc.connect(glb_connection_str)
    cursor = conn.cursor()
    employee_id = [x.personelID for x in glb_employees if x.Persname == glb_employeeselected]
    cursor.execute(
        "select  saleDate, salesID,  salesLineID,personelID, SalesModels.productID, amount, productRetailPrice, "
        "ProductName, typeOfCollection from dbo.SalesModels "
        "left outer join ProductModels "
        "on (SalesModels.productID= ProductModels.productID) "
        "where personelID=? and typeOfCollection=?",
        employee_id[0], typeOfCollection)
    glb_sales_line_id = 1
    for row in cursor:
        glb_customer_no = row[1]
        salesObj = Sales()
        salesObj.saleDate = row[0]
        salesObj.salesID = row[1]
        salesObj.salesLineID = row[2]
        salesObj.personelID = row[3]
        salesObj.productID = row[4]
        salesObj.amount = row[5]
        salesObj.retailPrice = row[6]
        salesObj.productName = row[7]
        salesObj.typeOfCollection = row[8]
        glb_sales.append(salesObj)
        glb_sales_line_id = glb_sales_line_id + 1
    cursor.close


def load_products(self, ID):
    conn = pyodbc.connect(glb_connection_str)
    cursor = conn.cursor()
    cursor.execute(
        "Select  TeraziID, [dbo].[ProductModels].productID, productName, productRetailPrice from [dbo].[ProductModels]"
        " left outer join [dbo].[TeraziScreenMapping] on "
        "([dbo].[TeraziScreenMapping].productID=[dbo].[ProductModels].productID)"
        "where TeraziID=?", ID)
    glb_product_names.clear()
    for row in cursor:
        productObj = Product()
        productObj.teraziID = row[0]
        productObj.productID = row[1]
        productObj.productName = row[2]
        productObj.price = float(row[3])
        glb_product_names.append(productObj)
    cursor.close()


class loadTables:

    def __init__(self):
        global glb_scaleId
        global glb_sales_line_id
        global glb_base_weight
        global glb_customer_no

        load_products(self, 1)
        glb_scaleId = 0
        glb_sales_line_id = 1
        glb_base_weight = 0
        glb_customer_no = 0
        conn = pyodbc.connect(glb_connection_str)
        cursor = conn.cursor()
        cursor.execute("Select  TeraziID, teraziName from [dbo].[TeraziTable]")
        for row in cursor:
            reyonObj = Reyon()
            reyonObj.teraziID = row[0]
            reyonObj.ReyonName = row[1]
            glb_reyons.append(reyonObj)
        cursor.execute("Select personelID, persName,persSurname  from  [dbo].[employeesModels]")
        for row in cursor:
            employeeObj = Employee()
            employeeObj.Persname = row[1] + " " + row[2]
            employeeObj.personelID = row[0]
            glb_employees.append(employeeObj)


def maininit(top, gui, *args, **kwargs):
    global w, top_level, root
    w = gui
    top_level = top
    root = top


def vp_start_gui():
    '''Starting point when module is the main routine.'''
    global w, root, top
    root = tk.Tk()
    top = MainWindow(root)
    maininit(root, top)
    root.mainloop()


class MainWindow(tk.Tk):

    def message_box_frame_def(self):
        global top
        self.message_box_frame.place(relx=0.0, rely=0.900, relheight=0.10, relwidth=0.994)
        self.message_box_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.message_box_frame.configure(highlightbackground="#f0f0f0", width=795)
        self.message_box_text = tk.Text(self.message_box_frame, height=1, width=80, font=("Arial Bold", 12),
                                    bg='dark red', fg="white")
        self.message_box_text.place(relx=0.0, rely=0.0, relheight=0.60, relwidth=0.994)

    def paging_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.paging_frame.place(relx=0.28, rely=0.560, relheight=0.120, relwidth=0.700)
        self.paging_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        next_button = tk.Button(self.paging_frame, text="Sonraki Sayfa")
        next_button.configure(activebackground="#ececec", activeforeground="#000000", background="red")
        next_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        next_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                         wraplength=130)
        next_button.configure(command=lambda btn=next_button: self.next_product_button_clicked())
        next_button.grid(row=0, column=2)
        previous_button = tk.Button(self.paging_frame, text="Önceki Sayfa")
        previous_button.configure(activebackground="#ececec", activeforeground="#000000", background="red")
        previous_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        previous_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                         wraplength=130)
        previous_button.configure(command=lambda btn=previous_button: self.previous_product_button_clicked())
        previous_button.grid(row=0, column=0)

    def employee_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        for child in self.product_frame.winfo_children():
            child.destroy()
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        row_size, col_size = 4, 3
        for btn_no, employee in enumerate(glb_employees):
            button = tk.Button(self.product_frame, text=employee.Persname)
            button.configure(command=lambda btn=button: self.employee_button_clicked(btn))
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9", disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=13, height=2)
            button.configure(wraplength=130)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)

    def display_frame_def(self):
        global top

        self.display_frame.place(relx=0.0, rely=0.0, relheight=0.100, relwidth=0.994)
        self.product_frame.configure(width=795)
        self.customer_no = tk.Text(self.display_frame, height=1, width=4, font=("Arial Bold", 25),
                                   bg='dark blue', fg="white")
        self.scale_display = tk.Text(self.display_frame, height=1, width=12, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.scale_type.insert(END, "Kg")
        self.customer_no.insert(END, "0")
        reyon_names = []
        for index, reyonObj in enumerate(glb_reyons):
            reyon_names.append(reyonObj.ReyonName)
        self.select_reyon = Combobox(self.display_frame, font=("Arial Bold", 22), values=reyon_names)
        self.select_reyon.bind("<<ComboboxSelected>>", self.checkreyon)
        self.select_reyon
        self.select_reyon.grid(row=0, column=0)
        self.customer_no.grid(row=0, column=1)
        self.scale_display.grid(row=0, column=2)
        self.scale_type.grid(row=0, column=3)

    def add_product_buttons(self):
        global glb_product_page
        font11 = "-family {Segoe UI} -size 11 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        for child in self.product_frame.winfo_children():
            child.destroy()
        row_size, col_size = 4, 3
        lower_product_cnt = glb_product_page*row_size*col_size
        while lower_product_cnt > len(glb_product_names):
            glb_product_page = glb_product_page-1
            lower_product_cnt = glb_product_page*row_size*col_size
        upper_product_cnt = lower_product_cnt+12
        if upper_product_cnt > len(glb_product_names):
            upper_product_cnt = len(glb_product_names)
        btn_no = 0
        while lower_product_cnt < upper_product_cnt:
            prod = glb_product_names[lower_product_cnt]
            button = tk.Button(self.product_frame, text=prod.productName)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                             wraplength=130)
            button.configure(command=lambda btn=button: self.product_button_clicked(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
            btn_no=btn_no+1
            lower_product_cnt = lower_product_cnt+1


    def product_frame_def(self):
        global top

        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        self.add_product_buttons()

    def productssold_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 8 -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"
        self.products_sold_frame.place(relx=0.0, rely=0.110, relheight=0.550, relwidth=0.280)
        self.products_sold_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9",
                                           highlightbackground="#d9d9d9")
        self.products_sold_frame.configure(highlightcolor="black", width=155)
        self.entry_products = tk.Text(self.products_sold_frame)
        self.entry_products.place(relx=0.010, rely=0.02, relheight=0.84, relwidth=0.700)
        self.entry_products.configure(font=font11)
        self.entry_products.configure(takefocus="")
        self.entry_calculatedtotal = tk.Text(self.products_sold_frame)
        self.entry_calculatedtotal.place(relx=0.720, rely=0.02, relheight=0.84, relwidth=0.240)
        self.entry_calculatedtotal.configure(font=font11, takefocus="")
        self.label_sum = tk.Label(self.products_sold_frame)
        self.label_sum.place(relx=0.040, rely=0.88, relheight=0.10, relwidth=0.300)
        self.label_sum.configure(background="#d9d9d9")
        self.label_sum.configure(disabledforeground="#a3a3a3")
        self.label_sum.configure(font=font9)
        self.label_sum.configure(foreground="#000000")
        self.label_sum.configure(text='''Toplam''')
        self.entry_sum = tk.Text(self.products_sold_frame, height=1, width=80, font=("Arial Bold", 12))
        self.entry_sum.place(relx=0.650, rely=0.88, relheight=0.10, relwidth=0.350)

    def functions_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"

        self.functions_frame.place(relx=0.0, rely=0.700, relheight=0.200, relwidth=0.994)
        self.functions_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.functions_frame.configure(highlightbackground="#f0f0f0", width=795)

        self.btn_dara = tk.Button(self.functions_frame)
        self.btn_dara.configure(command=lambda btn=self.btn_dara: self.btn_dara_clicked())
        self.btn_dara.place(relx=0.013, rely=0.050, height=35, width=160)
        self.btn_dara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_dara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_dara.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", text='''Dara''',
                                width=15)

        self.btn_changeuser = tk.Button(self.functions_frame)
        self.btn_changeuser.configure(command=lambda btn=self.btn_changeuser: self.btn_change_user_clicked())
        self.btn_changeuser.place(relx=0.264, rely=0.050, height=35, width=160)
        self.btn_changeuser.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_changeuser.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_changeuser.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Çalışan Değiştir''', width=15)

        self.btn_newcustomer = tk.Button(self.functions_frame)
        self.btn_newcustomer.configure(command=lambda btn=self.btn_newcustomer: self.new_customer_clicked())
        self.btn_newcustomer.place(relx=0.516, rely=0.050, height=35, width=160)
        self.btn_newcustomer.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_newcustomer.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_newcustomer.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                       text='''Yeni Müşteri''', width=15)

        self.btn_cancelsale = tk.Button(self.functions_frame)
        self.btn_cancelsale.configure(command=lambda btn=self.btn_cancelsale: self.btn_cancelsale_clicked())
        self.btn_cancelsale.place(relx=0.767, rely=0.050, height=35, width=160)
        self.btn_cancelsale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cancelsale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_cancelsale.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Satışı İptal Et''', width=15)

        self.btn_cleardara = tk.Button(self.functions_frame)
        self.btn_cleardara.configure(command=lambda btn=self.btn_cleardara: self.btn_cleardara_clicked())
        self.btn_cleardara.place(relx=0.013, rely=0.500, height=35, width=160)
        self.btn_cleardara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cleardara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                     text='''Darayı Temizle''', width=15)

        self.btn_savesale = tk.Button(self.functions_frame)
        self.btn_savesale.configure(command=lambda btn=self.btn_savesale: self.btn_savesale_clicked())
        self.btn_savesale.place(relx=0.264, rely=0.500, height=35, width=160)
        self.btn_savesale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_savesale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                    text='''Satışı Kaydet''', width=15)

        self.btn_sendcashier = tk.Button(self.functions_frame)
        self.btn_sendcashier.configure(command=lambda btn=self.btn_sendcashier: self.btn_sendcashier_clicked())
        self.btn_sendcashier.place(relx=0.516, rely=0.500, height=35, width=160)
        self.btn_sendcashier.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_sendcashier.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_sendcashier.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                       text='''Kasaya Gönder''', width=15)

        self.btn_clearlasttransaction = tk.Button(self.functions_frame)
        self.btn_clearlasttransaction.configure(
            command=lambda btn=self.btn_clearlasttransaction: self.btn_clearlasttransaction_clicked())
        self.btn_clearlasttransaction.place(relx=0.767, rely=0.500, height=35, width=160)
        self.btn_clearlasttransaction.configure(activebackground="#ececec", activeforeground="#000000",
                                                background="#d9d9d9")
        self.btn_clearlasttransaction.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_clearlasttransaction.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                                text='''Son İşlemi Sil''', width=15)

    def next_product_button_clicked(self):
        global glb_product_page
        glb_product_page = glb_product_page + 1
        self.add_product_buttons()

    def previous_product_button_clicked(self):
        global glb_product_page
        if glb_product_page > 0:
            glb_product_page = glb_product_page - 1
        self.add_product_buttons()

    def btn_sendcashier_clicked(self):
        global glb_customer_no
        global glb_sales_line_id

        sales_save(-1)
        sales_update(0)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        glb_customer_no = 0
        glb_sales_line_id = 1
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")

    def btn_change_user_clicked(self):
        global top
        global glb_employeeselected
        global glb_customer_no

        glb_sales.clear()
        glb_customer_no = 0
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.employee_frame_def()
        glb_employeeselected = ""

    def new_customer_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        salescounterobj = SalesCounter()
        glb_customer_no = salescounterobj.getcounter()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        glb_sales_line_id = 1

    def btn_cancelsale_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        sales_save(-2)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1

    def btn_savesale_clicked(self):
        global glb_sales_line_id

        sales_save(-1)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1
        self.btn_change_user_clicked()

    def btn_dara_clicked(self):
        global glb_base_weight
        glb_base_weight = float(self.scale_display.get("1.0", END).strip("\n"))
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, "0.000".rjust(20))

    def btn_cleardara_clicked(self):
        global glb_base_weight
        glb_base_weight = 0
        floatval = float(filter_data) - glb_base_weight
        mydata = "{:10.3f}".format(floatval)
        mydata = mydata.rjust(20)
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, mydata)

    def btn_clearlasttransaction_clicked(self):
        glb_sales.pop(-1)
        self.update_products_sold()

    def checkreyon(self, event: object):
        global glb_scaleId
        global glb_employeeselected

        self.message_box_text.delete("1.0", END)
        if glb_employeeselected != "":
            tt = self.select_reyon.get()
            glb_scaleId = self.select_reyon.current()
            teraziID = [x.teraziID for x in glb_reyons if x.ReyonName == tt][0]
            load_products(self, teraziID)
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.product_frame_def()
            self.functions_frame_def()
            self.select_reyon.current(glb_scaleId)
        else:
            self.message_box_text.insert(END, "Çalışan seçilmeden işleme devam edilemez")

    def employee_button_clicked(self, btn):
        global glb_scaleId
        global glb_employeeselected


        self.message_box_text.delete("1.0", END)
        glb_scaleId = self.select_reyon.current()
        if glb_scaleId != -1:
            glb_employeeselected = btn.cget("text")
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.display_frame.grid(row=0, column=0, columnspan=2)
            self.products_sold_frame.grid(row=1, column=0, rowspan=2)
            self.product_frame.grid(row=1, column=1)
            self.paging_frame.grid(row=2, column=1)
            self.functions_frame.grid(row=3, column=0, columnspan=2)
            self.message_box_frame.grid(row=4, column=0, columnspan=2)
            self.functions_frame_def()
            self.employee_frame_def()
            self.paging_frame_def()
            self.productssold_frame_def()
            self.message_box_frame_def()
            tt = self.select_reyon.get()
            teraziID = [x.teraziID for x in glb_reyons if x.ReyonName == tt][0]
            load_products(self, teraziID)
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.product_frame_def()
            self.functions_frame_def()
            self.select_reyon.current(glb_scaleId)
            sales_load(-1)
            self.update_products_sold()
            self.customer_no.delete('1.0', END)
            self.customer_no.insert(END, glb_customer_no)
        else:
            self.message_box_text.insert(END, "Reyon Seçimini Yapmadan Personel Seçimi Yapılamaz")

    def update_products_sold(self):
        self.entry_products.delete("1.0", END)
        self.entry_calculatedtotal.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.entry_products.insert(END, salesObj.productName + "\n")
            calculated_price = float(salesObj.amount * salesObj.retailPrice)
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}".format(calculated_price).rjust(8, ' ') + "\n"
            self.entry_calculatedtotal.insert(END, myData)
        self.entry_sum.delete("1.0", END)
        self.entry_sum.insert(END, "{:5.2f}".format(sum_calculated_price).rjust(8, ' '))

    def product_button_clicked(self, btn):
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        if (glb_customer_no != 0):
            salesObj = Sales()
            salesObj.productName = btn.cget("text")
            salesObj.salesID = glb_customer_no
            salesObj.salesLineID = glb_sales_line_id
            glb_sales_line_id = glb_sales_line_id + 1
            salesObj.personelID = [x.personelID for x in glb_employees if x.Persname == glb_employeeselected][0]
            salesObj.amount = float(self.scale_display.get("1.0", END).strip("\n"))
            salesObj.retailPrice = [x.price for x in glb_product_names if x.productName == salesObj.productName][0]
            salesObj.productID = [x.productID for x in glb_product_names if x.productName == salesObj.productName][0]
            salesObj.typeOfCollection = 0
            glb_sales.append(salesObj)
            self.update_products_sold()
        else:
            self.message_box_text.insert(END, "Yeni Müşteri Seçilmeden Ürün Seçimi Yapılamaz")

    def __init__(self, top=None):

        w, h = top.winfo_screenwidth(), root.winfo_screenheight()
        top.geometry("%dx%d+0+0" % (w, h))
        """top.geometry("800x480+1571+152")"""
        top.title("Terazi Ara Yüzü")
        top.configure(background="#d9d9d9")
        windows_env = 0
        serial_data = ''
        filter_data = ''
        update_period = 60
        serial_object = None
        loadTables()
        """Create frames"""
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
        self.display_frame_def()
        self.functions_frame_def()
        self.employee_frame_def()
        self.paging_frame_def()
        self.productssold_frame_def()
        self.message_box_frame_def()
        new_data = threading.Event()
        t2 = threading.Thread(target=update_gui, args=(self.scale_display, new_data,))
        t2.daemon = True
        t2.start()
        if windows_env:
            connect(new_data, 1, 9600, '5')
        else:
            connect(new_data, 2, 9600, 'USB0')


def connect(new_data, env, baud, port):
    """The function initiates the Connection to the UART device with the Port and Buad fed through the Entry
    boxes in the application.

    The radio button selects the platform, as the serial object has different key phrases
    for Linux and Windows. Some Exceptions have been made to prevent the app from crashing,
    such as blank entry fields and value errors, this is due to the state-less-ness of the
    UART device, the device sends data at regular intervals irrespective of the master's state.

    The other Parts are self explanatory.
    """

    global serial_object

    try:
        if env == 2:
            try:
                serial_object = serial.Serial('/dev/tty' + str(port), baud)
            except:
                print("Cant Open Specified Port")
        elif env == 1:
            serial_object = serial.Serial('COM' + str(port), baud)
    except ValueError:
        print("Enter Baud and Port")
        return
    t1 = threading.Thread(target=get_data,
                          args=(new_data,))
    t1.daemon = True
    t1.start()


def get_data(new_data):
    """This function serves the purpose of collecting data from the serial object and storing
    the filtered data into a global variable.

    The function has been put into a thread since the serial event is a blocking function.
    """
    global serial_object
    global filter_data
    filter_data = ""
    while (1):
        try:
            serial_data = str(serial_object.readline(), 'utf-8')
            serial_data = serial_data.rstrip('\r')
            serial_data = serial_data.rstrip('\n')
            if (serial_data[0:1] == '+') and (filter_data != serial_data[4:serial_data.index("kg")]):
                filter_data = serial_data[4:serial_data.index("kg")]
                new_data.set()
                print(filter_data)
            else:
                pass

        except TypeError:
            pass
        except UnicodeDecodeError:
            pass


def update_gui(scale_display, new_data):
    """" This function is an update function which is also threaded. The function assimilates the data
    and applies it to it corresponding progress bar. The text box is also updated every couple of seconds.

    A simple auto refresh function .after() could have been used, this has been avoid purposely due to
    various performance issues.


    """
    global filter_data
    global glb_base_weight

    while (1):
        event_is_set = new_data.wait()
        new_data.clear()
        if filter_data:
            scale_display.delete(1.0, END)
            floatval = float(filter_data) - glb_base_weight
            mydata = "{:10.3f}".format(floatval)
            mydata = mydata.rjust(20)
            scale_display.insert(END, mydata)


if __name__ == '__main__':
    vp_start_gui()

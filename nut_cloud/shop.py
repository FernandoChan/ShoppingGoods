from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)
from werkzeug.exceptions import abort
from nut_cloud.auth import login_required
from nut_cloud.db import get_db
import functools
import os
import os, fnmatch
import markdown2
from flask_bootstrap import Bootstrap

bp = Blueprint('shop', __name__, url_prefix='/shop')
basedir="../upload_files/anyone/shop"
#bootstrap = Bootstrap (bp)

def find(pattern, path):
    result = []
    for root, _, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def shop_user_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.shopuser is None:
            flash("You haven't complete your user info",category="error")
            return redirect(url_for('shop.adduserinfo'))
        return view(**kwargs)

    return wrapped_view

def shop_admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.shopuser is None:
            flash("You haven't complete your user info and shipping address",category="error")
            return redirect(url_for('shop.adduserinfo'))
        if g.shopuser['isadmin'] == False:
            flash("You are not the administrator",category="error")
            return redirect(url_for('index'))
        return view(**kwargs)

    return wrapped_view

@bp.route('/')
def index():
    db=get_db()
    category=request.values.get('category')
    goods=None
    if category is None:
        goods=db.execute(
            'SELECT id, name, value, type, amount FROM goods where isOnsale=1'
        ).fetchall()
    else:
        goods=db.execute(
            'SELECT id, name, value, type, amount FROM goods where isOnsale=1 AND type = ?',
            (category,)
        ).fetchall()
    categories=db.execute(
        'SELECT name FROM category'
    ).fetchall()
    return render_template('shop/index.html', goods=goods,categories=categories,search=False)


@bp.route('/adduserinfo',methods=['POST','GET'])
@login_required
def adduserinfo():
    db=get_db()
    info=db.execute(
        'SELECT * FROM shopuser WHERE userid = ?',
        (g.user['id'],)
    ).fetchone()
    if info is not None:
        flash("You have already registered")
        return redirect(url_for("shop.index"))
    if request.method == 'GET':
        return render_template('shop/userinfo.html')
    isadmin=g.user['isadmin']
    address=request.form.get('address')
    postalcode=request.form.get('postalcode')
    phone=request.form.get('phone')
    email=request.form.get('email')
    db.execute(
        'INSERT INTO shopuser (userid, phone, email, address, postalcode, isadmin) VALUES (?, ?, ?, ?, ?, ?)',
        (g.user['id'],phone,email,address,postalcode,isadmin,)
    )
    db.commit()
    return redirect(url_for('shop.index'))

@bp.route('/addgood',methods=['POST','GET'])
@shop_admin_required
def addgood():
    if request.method=='GET':
        db=get_db()
        categories=db.execute(
            'SELECT name FROM category'
        ).fetchall()
        return render_template('shop/addgood.html',categories=categories)
    name=request.form.get("name")
    value=request.form.get("value")
    amount=request.form.get("amount")
    gtype=request.form.get("type")
    description=request.form.get("description")
    db=get_db()
    info=db.execute(
        'INSERT INTO goods (name, value, amount, type, isOnsale, description) VALUES (?, ?, ?, ?, ?, ?)',
        (name, value, amount, gtype, 1, description,)
    )
    db.commit()
    return redirect(url_for('shop.addpic',id=info.lastrowid))

#
# @bp.route('/addreview/{{}}')
# def addreview():
#     review = request.form.get("review")
#     db = get_db()
#     info = db.execute(
#         'INSERT INTO goods (reviews) VALUES(?)',
#         (review)
#     )
#     db.commit()
#     # 导航到下一个商品
#     return redirect('/shop/detail/{{idnum}}')


@bp.route('/addpic',methods=['POST','GET'])
@shop_admin_required
def addpic():
    if request.method=='GET':
        return render_template('shop/addpic.html', id=request.values['id'])
    if 'file' not in request.files:
        flash('No file part',category="error")
        return redirect(request.referrer)
    try:
        file_path=os.path.abspath(find(str(request.form['id'])+'.*',basedir)[0])
        if os.path.isfile(file_path):
            os.remove(file_path)
    except IndexError:
        pass
    files = request.files.getlist("file")
    for file in files:
        split_file_name = os.path.splitext(file.filename)
        path = str(request.form['id']) + split_file_name[1]
        path=os.path.join(basedir, path)
        file.save(path)
    return redirect(url_for('shop.index'))

@bp.route('/getpic/<int:idnum>')
def getpic(idnum):
    try:
        path=os.path.abspath(find(str(idnum)+'.*',basedir)[0])
        return send_file(path, conditional=True)
    except IndexError:
        return 'Error',404

@bp.route('/detail/<int:idnum>')
def detail(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ?',
        (idnum,)
    ).fetchone()
    if good is None:
        flash("不存在该商品",category="error")
        return redirect(url_for("shop.index"))
    htmlDescription =markdown2.markdown(good['description'])
    return render_template('shop/detail.html',good=good,html=htmlDescription)

@bp.route('/amendgood/<int:idnum>',methods=['POST','GET'])
@shop_admin_required
def amendgood(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ?',
        (idnum,)
    ).fetchone()
    if good is None:
        flash("不存在该商品",category="error")
        return redirect(url_for("shop.index"))
    if request.method=='GET':
        categories=db.execute(
            'SELECT name FROM category'
        ).fetchall()
        return render_template('shop/amendgood.html',good=good,categories=categories)
    name=request.form.get("name")
    value=request.form.get("value")
    amount=request.form.get("amount")
    gtype=request.form.get("type")
    description=request.form.get("description")
    db.execute(
        'UPDATE goods SET name = ?, value = ?, amount = ?, type = ?, description = ? WHERE id = ?',
        (name, value, amount, gtype, description,idnum,)
    )
    db.commit()
    return redirect(url_for('shop.addpic',id=idnum))

@bp.route('/deletegood/<int:idnum>',methods=['POST'])
@shop_admin_required
def deletegood(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ?',
        (idnum,)
    ).fetchone()
    if good is None:
        flash("不存在该商品",category="error")
        return redirect(url_for("shop.index"))
    db.execute(
        'UPDATE goods SET isOnSale=0 WHERE id = ?',
        (idnum,)
    )
    db.commit()
    flash("商品成功删除")
    return redirect(request.referrer)

@bp.route('/changeuserinfo',methods=['GET','POST'])
@shop_user_required
def changeuserinfo():
    if request.method == 'GET':
        return render_template('shop/userinfo.html',i=g.shopuser)
    address=request.form.get('address')
    postalcode=request.form.get('postalcode')
    phone=request.form.get('phone')
    email=request.form.get('email')
    db=get_db()
    db.execute(
        'UPDATE shopuser SET phone = ?, email = ?, address = ?, postalcode = ? WHERE userid = ?',
        (phone,email,address,postalcode,g.user['id'],)
    )
    db.commit()
    return redirect(url_for('shop.index'))

@bp.route('/search')
def search():
    search_name=request.values.get('search_name')
    category=request.values.get('category')
    db=get_db()
    goods=None
    if search_name is None:
        search_name=''
    if category is not None:
        goods=db.execute(
            'SELECT id, name, value, type, amount FROM goods where isOnsale=1 AND name LIKE ? AND type = ?',
            ("%"+search_name+"%",category,)
        ).fetchall()
    else:
        goods=db.execute(
            'SELECT id, name, value, type, amount FROM goods where isOnsale=1 AND name LIKE ?',
            ("%"+search_name+"%",)
        ).fetchall()
    categories=db.execute(
        'SELECT name FROM category'
    ).fetchall()
    return render_template('shop/index.html', goods=goods,categories=categories,search=True,search_name=search_name)

@bp.route('/buy/<int:idnum>',methods=['POST'])
@shop_user_required
def buy(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ? AND isOnsale = 1',
        (idnum,)
    ).fetchone()
    if good is None:
        flash("This does not exist!",category="error")
        return redirect(url_for("shop.index"))
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchone()
    if info is None:
        db.execute(
            'INSERT INTO cart (goodid, amount, userid) VALUES (?, ?, ?)',
            (idnum, 1, g.user['id'],)
        )
    else:
        db.execute(
            'UPDATE cart SET amount = ? WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
            (info['amount']+1,idnum,g.user['id'],)
        )
    db.commit()
    flash("Added to Cart!")
    return redirect(request.referrer)

@bp.route('/minusone/<int:idnum>',methods=['POST'])
@shop_user_required
def minusone(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ? AND isOnsale = 1',
        (idnum,)
    ).fetchone()
    if good is None:
        flash("Does not exist",category="error")
        return redirect(url_for("shop.index"))
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchone()
    if info is None:
        flash("Illegal Ops",category="error")
        return redirect(request.referrer)
    amount=info['amount']-1
    if amount == 0:
        db.execute(
            'DELETE FROM cart WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
            (idnum,g.user['id'],)
        )
    else:
        db.execute(
            'UPDATE cart SET amount = ? WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
            (amount,idnum,g.user['id'],)
        )
    db.commit()
    flash("Delete succed")
    return redirect(request.referrer)

@bp.route('/delete/<int:idnum>',methods=['POST'])
@shop_user_required
def delete(idnum):
    db=get_db()
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchone()
    if info is None:
        flash("Illegal delete",category="error")
        return redirect(request.referrer)
    db.execute(
        'DELETE FROM cart WHERE goodid = ? AND ticketid IS NULL AND userid = ?',
        (idnum,g.user['id'],)
    )
    db.commit()
    flash("All goods have been remove from your cart")
    return redirect(request.referrer)

@bp.route('/cart')
@shop_user_required
def cart():
    db=get_db()
    goods=db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL',
        (g.user['id'],)
    ).fetchall()
    amount=db.execute(
        'SELECT SUM(amount*value) AS VALUE FROM (SELECT cart.amount, goods.* \
        FROM cart INNER JOIN goods ON goods.id = cart.goodid \
        WHERE cart.userid = ? AND cart.ticketid IS NULL AND goods.isOnsale=1)',
        (g.user['id'],)
    ).fetchone()['value']
    return render_template('shop/cart.html',goods=goods,amount=amount)

@bp.route('/emptycart',methods=['POST'])
@shop_user_required
def emptycart():
    db=get_db()
    goods = db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL',
        (g.user['id'],)
    ).fetchall()
    if goods == []:
        flash("Your cart is empty", category="error")
        return redirect(request.referrer)

    db.execute(
        'DELETE FROM cart WHERE ticketid IS NULL AND userid = ?',
        (g.user['id'],)
    )
    db.commit()
    return redirect(request.referrer)


@bp.route('/calccart',methods=['POST'])
@shop_user_required
def calccart():
    db=get_db()
    goods=db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL',
        (g.user['id'],)
    ).fetchall()
    if goods == []:
        flash("Your cart is empty",category="error")
        return redirect(request.referrer)
    existedgoods=db.execute(
        'SELECT cart.amount AS cartamount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL AND goods.isOnsale=1',
        (g.user['id'],)
    ).fetchall()
    isValid=True
    for good in existedgoods:
        try:
            if good['amount'] is not None and good['amount']!='' and int(good['cartamount'])>int(good['amount']):
                isValid=False
                flash("There are only"+str(good['amount'])+str(good['id'])+" - "+good['name']+"in stock",category="error")
        except KeyError:
            pass
    if isValid==False:
        return redirect(request.referrer)
    for good in existedgoods:
        try:
            if good['amount'] is not None and good['amount']!='':
                db.execute(
                    'UPDATE goods SET amount = ? WHERE id = ?',
                    (int(good['amount'])-int(good['cartamount']),good['id'],)
                )
        except KeyError:
            pass
    deletedgoods=db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL AND goods.isOnsale=0',
        (g.user['id'],)
    ).fetchall()
    for deletedgood in deletedgoods:
        db.execute(
            'DELETE FROM cart WHERE userid = ? AND ticketid IS NULL AND goodid = ?',
            (g.user['id'],deletedgood['id'],)
        )
    if existedgoods == []:
        flash("It only contains off-shore goods",category="error")
        return redirect(request.referrer)
    amount=db.execute(
        'SELECT SUM(amount*value) AS VALUE \
        FROM (SELECT cart.amount, goods.* FROM cart INNER JOIN goods ON goods.id = cart.goodid \
        WHERE cart.userid = ? AND cart.ticketid IS NULL AND goods.isOnsale=1)',
        (g.user['id'],)
    ).fetchone()['value']
    info=db.execute(
        'INSERT INTO ticket (address, postalcode, value, userid, status) VALUES (?, ?, ?, ?, ?)',
        (g.shopuser['address'], g.shopuser['postalcode'], amount, g.user['id'],"pending",)
    )
    db.execute(
        'UPDATE cart SET ticketid = ? WHERE userid = ? AND ticketid IS NULL',
        (info.lastrowid, g.user['id'],)
    )
    db.commit()
    flash("Checkout Succed!")
    return redirect(url_for("shop.tickets"))

@bp.route('/tickets')
@shop_user_required
def tickets():
    db=get_db()
    tickets=db.execute(
        'SELECT * FROM ticket WHERE userid = ?',
        (g.user['id'],)
    ).fetchall()
    info=[]
    for ticket in tickets:
        goods=db.execute(
            'SELECT * FROM cart INNER JOIN goods ON cart.goodid=goods.id WHERE ticketid = ? AND userid = ?',
            (ticket['id'],g.user['id'],)
        ).fetchall()
        info.append((ticket,goods))
    return render_template('shop/tickets.html',info=info)

@bp.route('/cancelticket/<int:idnum>',methods=['POST'])
@shop_user_required
def cancelticket(idnum):
    db=get_db()
    info=db.execute(
        'SELECT status FROM ticket WHERE id = ? AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchone()
    if info is None or info['status'] != "pending":
        flash("Illegal Cancellations",category="error")
        return redirect(request.referrer)
    db.execute(
        'UPDATE ticket SET status = ? WHERE id = ? AND userid = ?',
        ("cancelled",idnum,g.user['id'],)
    )
    goods=db.execute(
        'SELECT * FROM cart WHERE ticketid = ? AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchall()
    for good in goods:
        oldamount=db.execute(
            'SELECT * FROM goods WHERE id = ?',
            (good['goodid'],)
        ).fetchone()
        try:
            if oldamount['amount'] is not None and oldamount['amount']!='':
                db.execute(
                    'UPDATE goods SET amount = ? WHERE id = ?',
                    (int(oldamount['amount'])+int(good['amount']),good['goodid'],)
                )
        except KeyError:
            pass
    db.commit()
    return redirect(request.referrer)


@bp.route('/finishticket/<int:idnum>',methods=['POST'])
@shop_admin_required
def finishticket(idnum):
    db=get_db()
    info=db.execute(
        'SELECT status FROM ticket WHERE id = ?',
        (idnum,)
    ).fetchone()
    if info is None or info['status'] != "pending":
        flash("Illegal Pending",category="error")
        return redirect(request.referrer)
    db.execute(
        'UPDATE ticket SET status = ? WHERE id = ?',
        ("finished",idnum,)
    )
    db.commit()
    return redirect(request.referrer)

@bp.route('/configtickets')
@shop_admin_required
def configtickets():
    db=get_db()
    tickets=db.execute(
        'SELECT ticket.id,ticket.address,value,created,status,phone,email,ticket.postalcode,username \
        FROM ticket INNER JOIN shopuser ON ticket.userid=shopuser.userid INNER JOIN USER ON shopuser.userid=user.id'
    ).fetchall()
    info=[]
    for ticket in tickets:
        goods=db.execute(
            'SELECT * FROM cart INNER JOIN goods ON cart.goodid=goods.id WHERE ticketid = ?',
            (ticket['id'],)
        ).fetchall()
        info.append((ticket,goods))
    return render_template('shop/configtickets.html',info=info)

@bp.route('/createcategory',methods=['GET','POST'])
@shop_admin_required
def createcategory():
    if request.method=='GET':
        return render_template('shop/createcategory.html')
    name=request.form.get('name')
    db=get_db()
    info=db.execute(
        'SELECT * FROM category WHERE name = ?',
        (name,)
    ).fetchone()
    if info is not None:
        flash("It is already existed",category="error")
        return redirect(request.referrer)
    db.execute(
        'INSERT INTO category (name) VALUES (?)',
        (name,)
    )
    db.commit()
    flash("Create Category Succeed!")
    return redirect(url_for("shop.createcategory"))

@bp.route('/categories')
@shop_admin_required
def categories():
    db=get_db()
    info=db.execute(
        'SELECT * FROM category'
    ).fetchall()
    return render_template("shop/categories.html",info=info)

@bp.route('/renamecategory/<int:idnum>',methods=['GET','POST'])
@shop_admin_required
def renamecategory(idnum):
    db=get_db()
    info=db.execute(
        'SELECT * FROM category WHERE id = ?',
        (idnum,)
    ).fetchone()
    if info is None:
        flash("The category doesn't exist")
        return redirect(request.referrer)
    if request.method=='GET':
        return render_template("shop/createcategory.html")
    name=request.form.get('name')
    oldname=db.execute(
        'SELECT name FROM category WHERE id = ?',
        (idnum,)
    ).fetchone()['name']
    db.execute(
        'UPDATE category SET name = ? WHERE id = ?',
        (name, idnum,)
    )
    db.execute(
        'UPDATE goods SET type = ? WHERE type = ?',
        (name,oldname,)
    )
    db.commit()
    return redirect(url_for("shop.categories"))

@bp.route('/deletecategory/<int:idnum>',methods=['POST'])
@shop_admin_required
def deletecategory(idnum):
    db=get_db()
    info=db.execute(
        'SELECT * FROM category WHERE id = ?',
        (idnum,)
    ).fetchone()
    if info is None:
        flash("The category doesn't exist")
        return redirect(request.referrer)
    oldname=db.execute(
        'SELECT name FROM category WHERE id = ?',
        (idnum,)
    ).fetchone()['name']
    db.execute(
        'DELETE FROM category WHERE id = ?',
        (idnum,)
    )
    db.execute(
        'UPDATE goods SET type = NULL WHERE type = ?',
        (oldname,)
    )
    db.commit()
    return redirect(url_for("shop.categories"))
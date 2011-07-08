#!/usr/bin/python
# -*- coding: utf-8 -*-

   ###########################################################################
 ##                 _____           _         _     _                       ##
##                 |  __ \         | |       | |   (_)                      ##
##                 | |__) |__ _ ___| |_  __ _| |__  _ _ __                  ##
##                 |  ___// _` / __| __|/ _` | '_ \| | '_ \                 ##
##                 | |   | (_| \__ \ |_| (_| | |_) | | | | |                ##
##                 |_|    \__,_|___/\__|\__,_|_.__/|_|_| |_|                ##
##                                                                          ##
##                        --  http://pastabin.org/  --                      ##
##                                                                          ##
##                                                                          ##
## Pastabin - A pastebin with a lot of taste                                ##
##                                                                          ##
## Copyright (C) 2011  Kozea                                                ##
##                                                                          ##
## This program is free software: you can redistribute it and/or modify     ##
## it under the terms of the GNU Affero General Public License as published ##
## by the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                      ##
##                                                                          ##
## This program is distributed in the hope that it will be useful,          ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of           ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            ##
## GNU Affero General Public License for more details.                      ##
##                                                                          ##
## You should have received a copy of the GNU Affero General Public License ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>.    ##
##                                                                          ##
##                                                                          ##
## Authored by: Amardine DAVID <amardine.david@kozea.fr>                    ##
## Authored by: Jérôme DEROCK <jerome.derock@kozea.fr>                      ##
## Authored by: Fabien LOISON <fabien.loison@kozea.fr>                      ##
##                                                                         ##
###########################################################################


__app_name__ = "PastaBin"
__version__ = "0.1"


from datetime import datetime
from hashlib import sha256

from flask import *
from multicorn.declarative import declare, Property
from multicorn.requests import CONTEXT as c
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers import get_lexer_for_filename
from pygments.lexers import guess_lexer
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Number

from access_points import *


app = Flask(__name__)
app.jinja_env.autoescape = True
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


class PygmentsStyle(Style):
    """Pygments style based on Solarized."""
    styles = {
        Keyword: '#b58900',
        Name: '#cb4b16',
        Comment: '#839496',
        String: '#2aa198',
        Error: '#dc322f',
        Number: '#859900'}


@app.template_filter("date_format")
def pretty_datetime(d):
    return d.strftime("%A %d. %B %Y @ %H:%M:%S").decode('utf-8')


@app.template_filter("snip_user")
def snip_user(user):
    if type(user) != unicode:
        return 'Guest'
    else:
        return user


@app.template_filter("check_title")
def check_title(title):
    if title == '':
        return 'Unamed snippet'
    else:
        return title


def get_page_informations(title="Unknown", menu_active=None):
    """Retun various informations like the menu, the page title,...

    Arguments:
        title -- The page title
        menu_active -- The name of the current page
    """
    menu_items = [
            {
                'name': "index",
                'title': "Home",
                'url': url_for("index"),
                'active': False,
            },
            {
                'name': "add",
                'title': "New snippet",
                'url': url_for("add_snippet_get"),
                'active': False,
            },
            ]
    if session.get("login", False):
        menu_items.append({
            'name': "my_snippets",
            'title': "My snippets",
            'url': url_for("my_snippets"),
            'active': False,
            })
    for item in menu_items:
        if menu_active == item['name']:
            item['active'] = True
            break
    return {
            'menu': menu_items,
            'title': check_title(title),
            'appname': __app_name__,
            }


def get_user_id():
    """Return the user id if logged, 0 else"""
    return session.get("id", 0)


def ckeck_rights(snippet_id):
    item = Snippet.all.filter(c.id == snippet_id).one(None).execute()
    if item is not None and item['person'] is not None:
        if item["person"]["id"] == get_user_id() and get_user_id() != 0:
            return True
    return False


@app.route("/", methods=["GET"])
def index():
    return render_template(
            "index.html.jinja2",
            snippets=list(Snippet.all.sort(-c.date)[:10].execute()),
            page=get_page_informations(title="Home"),
            )


@app.route("/snippet/<int:snippet_id>", methods=["GET"])
@app.route("/s/<int:snippet_id>", methods=["GET"])
def get_snippet_by_id(snippet_id):
    item = Snippet.all.filter(c.id == snippet_id).one(None).execute()
    if item is not None:
        lexer = None
        try:
            lexer = get_lexer_by_name(item['language'].lower())
        except:
            try:
                lexer = get_lexer_for_filename(item['title'].lower())
            except:
                try:
                    lexer = guess_lexer(item['text'])
                except:
                    lexer = get_lexer_by_name("text")
        formatter = HtmlFormatter(
                linenos=True,
                style=PygmentsStyle,
                noclasses=True,
                nobackground=True,
                )
        item['text'] = highlight(item['text'], lexer, formatter)
        return render_template(
                "snippet.html.jinja2",
                snippet=item,
                page=get_page_informations(title=item['title']),
                )
    else:
        return abort(404)


@app.route("/my_snippets", methods=["GET"])
def my_snippets():
    if get_user_id() <= 0:
        return abort(403)
    item = Snippet.all.filter(c.person.id == get_user_id()).sort(-c.date).execute()
    if item is not None:
        return render_template(
                "my_snippets.html.jinja2",
                snippets=list(item),
                page=get_page_informations(
                    title="My snippets",
                    menu_active="my_snippets",
                    ),
                )
    else:
        return abort(404)


@app.route("/add", methods=["GET"])
def add_snippet_get(def_title="", def_lng="", def_txt=""):
    return render_template(
            "edit_snippet.html.jinja2",
            snip_title=def_title,
            snip_language=def_lng,
            snip_text=def_txt,
            action=url_for("add_snippet_post"),
            cancel=url_for("index"),
            page=get_page_informations(
                title="Add a new Snippet",
                menu_active="add",
                ),
            )


@app.route("/add", methods=["POST"])
def add_snippet_post():
    if len(request.form['snip_text']) > 0:
        item = Snippet.create({
            'person': get_user_id(),
            'date': datetime.now(),
            'language': request.form['snip_language'],
            'title': request.form['snip_title'],
            'text': request.form['snip_text'],
            })
        item.save()
        return redirect(url_for("get_snippet_by_id", snippet_id=item['id']))
    else:
        flash("The text field is empty...", "error")
        return add_snippet_get(
                request.form['snip_title'],
                request.form['snip_language'],
                request.form['snip_text'],
                )


@app.route("/modify/<int:id>", methods=["GET"])
def modify_snippet_get(id):
    if not ckeck_rights(id):
        return abort(403)
    item = Snippet.all.filter(c.id == id).one(None).execute()
    if item is not None:
        return render_template(
                "edit_snippet.html.jinja2",
                snip_title=item['title'],
                snip_language=item['language'],
                snip_text=item['text'],
                action=url_for("modify_snippet_post", id=id),
                cancel=url_for("get_snippet_by_id", snippet_id=id),
                page=get_page_informations(
                    title="Modify a snippet (%s)" % item['title'])
                )
    else:
        return abort(404)


@app.route("/modify/<int:id>", methods=["POST"])
def modify_snippet_post(id):
    if not ckeck_rights(id):
        return abort(403)
    item = Snippet.all.filter(c.id == id).one(None).execute()
    if item is not None and len(request.form['snip_text']) > 0:
        item['date'] = datetime.now()
        item['language'] = request.form['snip_language']
        item['title'] = request.form['snip_title']
        item['text'] = request.form['snip_text']
        item.save()
    else:
        flash("Error when modifying the snippet", "error")
    return redirect(url_for("get_snippet_by_id", snippet_id=item['id']))


@app.route("/delete/<int:id>", methods=["GET"])
def delete_snippet_get(id):
    if not ckeck_rights(id):
        return abort(403)
    item = Snippet.all.filter(c.id == id).one(None).execute()
    if item is not None:
        return render_template(
                "delete.html.jinja2",
                snip_id=id,
                snip_title=item['title'],
                page=get_page_informations(title="Delete a snippet"),
                )
    else:
        return abort(404)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_snippet_post(id):
    if not ckeck_rights(id):
        return abort(403)
    item = Snippet.all.filter(c.id == id).one(None).execute()
    if item is not None:
        item.delete()
        return redirect(url_for("index"))
    else:
        return abort(404)


@app.route('/connect', methods=('GET',))
def get_connect():
    return render_template(
            'connect.html.jinja2',
            page=get_page_informations(title="Connexion"),
            )


@app.route('/connect', methods=['POST'])
def connect():
    item = Person.all.filter(
        c.login.lower() == request.form['login'].lower()).one(None)
    item = item.execute()
    if item is not None:
        if '' == request.form.get('login', '') \
            or '' == request.form.get('password', ''):
                flash("Invalid login or password !", "error")
                return redirect(url_for("connect"))
        if item['password'] == sha256(request.form['password']).hexdigest():
            session['login'] = item['login']
            session['id'] = item['id']
            flash("Welcome %s !" % escape(session["login"]), "ok")
            return redirect(url_for("index"))
        else:
            flash("Invalid login or password !", "error")
            return redirect(url_for("connect"))
    else:
        flash("Invalid login or password !", "error")
        return redirect(url_for("connect"))


@app.route('/disconnect', methods=['GET'])
def disconnect():
    session['login'] = None
    session['id'] = None
    flash('You are disconnected !', "ok")
    return redirect(url_for("index"))


@app.route('/register', methods=['GET'])
def get_register(def_login='', def_email=''):
    return render_template(
            'account.html.jinja2',
            action=url_for("register"),
            login=def_login,
            email=def_email,
            page=get_page_informations(title="Register"),
            )


@app.route('/register', methods=['POST'])
def register():
    if '' == request.form.get('login', '') \
        or '' == request.form.get('password1', '') \
        or '' == request.form.get('password2', '') \
        or '' == request.form.get('email', '') :
        flash("Some fields are empty !", "error")
        return get_register(def_login=request.form.get('login'),
                def_email=request.form.get('email'))

    if request.form['password1'] != request.form['password2']:
        flash("Passwords are not same !", "error")
        return get_register(def_login=request.form.get('login'),
                def_email=request.form.get('email'))
    item = Person.all.filter(c.login.lower() == \
        request.form['login'].lower()).one(None).execute()
    if item is not None:
        flash("Your login already exists !", "error")
        return get_register(def_login='', def_email=request.form.get('email'))
    else:
        person = Person.create({
            'login': request.form['login'],
            'password': sha256(request.form['password2']).hexdigest(),
            'email': request.form['email'],
            })
        person.save()
        session['login'] = person['login']
        session['id'] = person['id']
    flash("Welcome %s !" % escape(session["login"]), "ok")
    return redirect(url_for("index"))


@app.route('/account', methods=['POST'])
def account():
    if not session.get("id"):
        return redirect(url_for("connect"))
    if '' == request.form.get('login', '') \
        or '' == request.form.get('email', ''):
        flash("Some fields are empty !", "error")
        return get_account(def_login=request.form.get('login'),
                def_email=request.form.get('email'))
    person = Person.all.filter(c.login.lower() == \
        request.form['login'].lower()).one(None).execute()
    item = Person.all.filter(c.id == session["id"]).one(None).execute()
    if person is not None and person['login'] != item['login']:
        flash("Your login already exists !", "error")
        return get_account(def_login='', def_email=request.form.get('email'))
    if item is not None:
        item["login"] = request.form["login"]
        item["email"] = request.form["email"]
        if request.form["password1"] or request.form["password2"] :
            if request.form["password1"] != request.form["password2"]:
                flash("Passwords are not same !", "error")
                return get_account(def_login=request.form.get('login'),
                        def_email=request.form.get('email'))
            else:
                item["password"] = sha256(request.form['password1']).hexdigest()
        item.save()
        session["login"] = request.form["login"]
        flash("Your account is been modify !", "ok")
    return redirect(url_for("index"))


@app.route('/account', methods=['GET'])
def get_account(def_login='', def_email=''):
    item = Person.all.filter(c.id == get_user_id()).one(None).execute()
    return render_template(
            'account.html.jinja2',
            action=url_for("account"),
            login=item['login'],
            email=item['email'],
            page=get_page_informations(title="Manage my account"),
            person=item
            )


if __name__ == '__main__':
#    app.run()
    app.run(debug=True)



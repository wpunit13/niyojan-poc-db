from flaskblog import create_app
# from models import User, Post

# Database structure put it in models later


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)

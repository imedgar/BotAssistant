#!/usr/bin/env python
import scrollphathd
from api.http import scrollphathd_blueprint
from scrollphathd.fonts import font3x5
from flask import Flask

# Set the font
scrollphathd.set_font(font3x5)
# Set the brightness
scrollphathd.set_brightness(0.5)
# Uncomment the below if your display is upside down
# (e.g. if you're using it in a Pimoroni Scroll Bot)
scrollphathd.rotate(degrees=180)

if __name__ == "__main__":
    app = Flask(__name__)

    app.register_blueprint(scrollphathd_blueprint)

    html = open('web-api.html', 'r').read()

    @app.route('/')
    def index():
        return html
    app.run(debug=True, host='0.0.0.0', port=5000)

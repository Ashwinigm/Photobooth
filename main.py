# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import firestore
from flask import current_app, flash, Flask, Markup, redirect, render_template
from flask import request, url_for
from google.cloud import error_reporting
import google.cloud.logging
import storage


# [START upload_image_file]
def upload_image_file(img):
    """
    Upload the user-uploaded file to Google Cloud Storage and retrieve its
    publicly-accessible URL.
    """
    if not img:
        return None

    public_url = storage.upload_file(
        img.read(),
        img.filename,
        img.content_type
    )

    current_app.logger.info(
        'Uploaded file %s as %s.', img.filename, public_url)

    return public_url
# [END upload_image_file]


app = Flask(__name__)
app.config.update(
    SECRET_KEY='secret',
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    ALLOWED_EXTENSIONS=set(['png', 'jpg', 'jpeg', 'gif'])
)

app.debug = False
app.testing = False

# Configure logging
if not app.testing:
    logging.basicConfig(level=logging.INFO)
    client = google.cloud.logging.Client()
    # Attaches a Google Stackdriver logging handler to the root logger
    client.setup_logging()


# @app.route('/')
# def list():   
#     start_after = request.args.get('start_after', None)
#     photos, last_title = firestore.next_page(start_after=start_after)

#     return render_template('list.html', photos=photos, last_title=last_title)
@app.route('/')
def fetch_all_photos():
    photos = firestore.fetch_all_photos()
    return render_template('index.html', photos=photos)


@app.route('/photos/<photo_id>')
def view(photo_id):
    photo = firestore.read(photo_id)
    print("PhotoID here is ")
    return render_template('view.html', photo=photo)


@app.route('/photos/add', methods=['GET', 'POST'])
def add():
    image_name=None
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)

        # If an image was uploaded, update the data to point to the new image.
        image_url = upload_image_file(request.files.get('image'))

        if image_url:
            data['imageUrl'] = image_url
            image_name = image_url.split('/')[-1]

        photo = firestore.create(data, photo_id=image_name)
        print(f"Photo here {photo}")

        return redirect(url_for('fetch_all_photos'))

    return render_template('form.html', action='Add', photo={})


@app.route('/photos/<photo_id>/edit', methods=['GET', 'POST'])
def edit(photo_id):
    photo = firestore.read(photo_id)

    if request.method == 'POST':
        data = request.form.to_dict(flat=True)

        # If an image was uploaded, update the data to point to the new image.
        image_url = upload_image_file(request.files.get('image'))
        
        if image_url:
            data['imageUrl'] = image_url

        photo = firestore.update(data, photo_id)

        return redirect(url_for('.view', photo_id=photo['id']))

    return render_template('form.html', action='Edit', photo=photo)


@app.route('/photos/<photo_id>/delete')
def delete(photo_id):
    firestore.delete(photo_id)
    return redirect(url_for('.logs'))


@app.route('/logs')
def logs():
    logging.info('Hey, you triggered a custom log entry. Good job!')
    flash(Markup('''You triggered a custom log entry. You can view it in the
        <a href="https://console.cloud.google.com/logs">Cloud Console</a>'''))
    return redirect(url_for('.logs'))


@app.route('/errors')
def errors():
    raise Exception('This is an intentional exception.')


# Add an error handler that reports exceptions to Stackdriver Error
# Reporting. Note that this error handler is only used when debug
# is False
@app.errorhandler(500)
def server_error(e):
    client = error_reporting.Client()
    client.report_exception(
        http_context=error_reporting.build_flask_context(request))
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


# This is only used when running locally. When running live, gunicorn runs
# the application.
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

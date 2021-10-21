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

# [START photobooth_firestore_client_import]
import time
from google.cloud import firestore
# [END photobooth_firestore_client_import]


def document_to_dict(doc):
    if not doc.exists:
        return None
    doc_dict = doc.to_dict()
    doc_dict['id'] = doc.id
    return doc_dict


def next_page(limit=10, start_after=None):
    db = firestore.Client()

    query = db.collection(u'Photo').limit(limit).order_by(u'title')

    if start_after:
        # Construct a new query starting at this document.
        query = query.start_after({u'title': start_after})

    docs = query.stream()
    docs = list(map(document_to_dict, docs))

    last_title = None
    if limit == len(docs):
        # Get the last document from the results and set as the last title.
        last_title = docs[-1][u'title']
    return docs, last_title


def read(photo_id):
    # [START photobooth_firestore_client]
    db = firestore.Client()
    photo_ref = db.collection(u'Photo').document(photo_id)
    snapshot = photo_ref.get()
    # [END photobooth_firestore_client]
    return document_to_dict(snapshot)


def update(data, photo_id=None):
    db = firestore.Client()
    photo_ref = db.collection(u'Photo').document(photo_id)
    photo_ref.set(data)
    return document_to_dict(photo_ref.get())


create = update


def delete(id):
    db = firestore.Client()
    photo_ref = db.collection(u'Photo').document(id)
    photo_ref.delete()

HUMANS = ['person', 'human', 'people', 'smile', 'eyebrow']
ANIMALS = ['animal', 'cats', 'dog', 'amphibians', 'fish', 'reptiles', 'arthopoda', 'invertebrates', 'bird']
FLOWER = ['flower']


def find_categories(labels):
    found = False
    categories = []
    for item in labels:
        label = item.lower()
        for i in HUMANS:
            if i in label:
                # print(f"Keshav for this label it is being tagged as human {label}")
                found = True
                categories.append('Humans')
        for i in ANIMALS:
            if i in label:
                # print(f"Keshav for this label it is being tagged as animal {label}")
                found = True
                categories.append('Animals')
        for i in FLOWER:
            if i in label:
                found = True
                categories.append('Flowers')
    if not found:
        categories = ['Others']
    final_categories = list(set(categories))
    return final_categories


def read_async(image_name, retry=0):
    data = read(image_name)
    if data or retry > 5:
        return data
    time.sleep(1+retry)
    retry += 1
    read_async(image_name, retry)

        


def fetch_all_photos():
    db = firestore.Client()
    final_response = {'Animals': [], 'Flowers': [], 'Others': [], 'Humans': []}

    query = db.collection(u'Photo').order_by(u'title')
    docs = query.stream()
    docs = list(map(document_to_dict, docs))
    for doc in docs:
        # Fetch all labels:
        image_name = doc['imageUrl'].split('/')[-1]
        # photo_label_info = db.collection(u'Photo').document(image_name)
        data = read_async(image_name)

        del data['id']
        if data and data.get('thumbnail') is True and data.get('labels'):
            doc.update(data)
            # https://storage.googleapis.com/thumbnails-final-photobooth-329701/human1-2021-10-21-190359.jpg
            doc.update({'thumbnailUrl': f"https://storage.googleapis.com/thumbnails-final-photobooth-329701/{image_name}"})
            categories= find_categories(data['labels'])
            print(f"Keshav {categories} for Image {image_name}")
            print(doc)
            for i in categories:
                final_response[i].append(doc)
        
    return final_response
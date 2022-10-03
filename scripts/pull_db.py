import os
import re
import yaml
import requests
import opengraph_parse
from slugify import slugify
from notion_client import Client
from notion2md.exporter.block import StringExporter


class Page:
    def __init__(self, data):
        self.data = data
        if data['cover'] is not None and 'external' in data['cover']:
            self.cover = requests.get(data['cover']['external']['url']).content
        else:
            self.cover = None

    @property
    def id(self):
        return self.data['id']

    @property
    def name(self):
        if len(self.data['properties']['Name']['title']) > 0:
            return self.data['properties']['Name']['title'][0]['plain_text']
        return ''

    @property
    def slug(self):
        return slugify(self.name)

    @property
    def summary(self):
        if len(self.data['properties']['Summary']['rich_text']) > 0:
            return self.data['properties']['Summary']['rich_text'][0]['plain_text']
        return ''

    @property
    def link(self):
        if self.data['properties']['URL']['url'] is not None:
            page = opengraph_parse.parse_page(
                self.data['properties']['URL']['url'],
                tags_to_search=['og:title', 'og:description', 'og:url', 'og:image'],
                fallback_tags={
                    'og:title': 'title',
                    'og:description': 'description'
                }
            )
            return {
                'title': page['og:title'],
                'description': page['og:description'],
                'website': page['og:url'],
                'image': page['og:image'],
            }
        return None

    @property
    def last_edited(self):
        return self.data['last_edited_time']

    @property
    def type(self):
        return self.data['properties']['Type']['select']['name']

    @property
    def genres(self):
        return [genre['name'] for genre in self.data['properties']['Genres']['multi_select']]

    @property
    def front_matter(self):
        data = {
            'title': self.name,
            'description': self.summary,
            'date': self.last_edited,
            'categories': [self.type],
            'tags': self.genres,
        }
        if self.cover is not None:
            data['image'] = 'cover.jpg'
        if self.link is not None:
            data['links'] = [self.link]
        return f'---\n{yaml.dump(data)}---\n'


notion = Client(auth=os.environ['NOTION_TOKEN'])

pages = notion.databases.query(
    database_id='0fd230e4-f6d3-4a43-b2da-453f0d71c2a6',
    filter={
        'property': 'Notes Status',
        'select': {
            'equals': 'Ready for Publication'
        }
    }
).get('results')

# Convert to wrapper class
pages = [Page(p) for p in pages]

for page in pages:
    md = StringExporter(block_id=page.id).export()
    md = re.sub(r'^\s*?!\[', '![', md)          # Remove any indented image tags
    md = re.sub(r'\*(.*?)\s\*', '*\g<1>* ', md) # Fix improperly formatted italics

    path = f'../content/post/{page.slug}/'
    os.makedirs(path, exist_ok=True)

    with open(f'{path}/index.md', 'w') as f:
        f.write(page.front_matter + md)

    if page.cover is not None:
        with open(f'{path}/cover.jpg', 'wb') as f:
            f.write(page.cover)

    # Set note status to "Published"
    notion.pages.update(
        page_id=page.id,
        properties={
            'Notes Status': {
                'select': {
                    'name': 'Published'
                }
            }
        }
    )

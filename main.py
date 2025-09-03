import schoolopy
from tqdm import tqdm
import json
from pathlib import Path
import argparse
import tomllib
import html as ht
import shutil
import datetime

now = datetime.datetime.now()
friendlydate = now.strftime("%b %-m, %Y")

# Define parser for CLI Args
parser = argparse.ArgumentParser(
                    prog='Schoology Backup',
                    description='Back up a bunch of helpful schoology data')

parser.add_argument("-c", "--config", type=Path, required=False, help="Path to a config file, default is \"config.toml\"")
parser.add_argument("-o", "--output", type=Path, required=False, help=f"Output directory, default is \"Schoology Backup - {friendlydate}\"")
parser.add_argument("-v", "--converted", action="store_true", help="Download the converted versions of files from Schoology (PDF instead of .docx, etc.)")

args = parser.parse_args()

# Define some configuration variables
config_path = args.config if args.config is not None else Path('config.toml')
root_path = Path(args.output) if args.output is not None else Path(f'Schoology Backup {friendlydate}')
root_path.mkdir(exist_ok=True)
shutil.copyfile(Path('resources') / Path('style.css'), root_path / Path('style.css'))
sections_root = (root_path / 'sections')
sections_root.mkdir(exist_ok=True)
main_data = {}
colors_to_emojis = {"red": "🔴", "orange": "🟠", "purple": "🟣", "blue": "🔵", "green": "🟢", "yellow": "🟡", "pink": "🩷", "black": "⚫"}

# Open the config file
with open(config_path, 'rb') as f:
    config = tomllib.load(f)

# Function definitions
def mkdir_if_not_exists(dir) -> Path:
    """Make a directory if it doesn't exist."""
    new_path = Path(dir)
    new_path.mkdir(exist_ok=True, parents=True)
    return new_path  

def get_item_data(item_id, section_id, item_type):
    """Helper function to get data for an item of varying type"""
    match item_type:
        case 'document':
            return sc.get_section_document(item_id, section_id)
        case 'assignment':
            return sc.get_assignment(item_id, section_id)
        case 'page':
            return sc.get_section_page(item_id, section_id, with_attachments=True)

def generate_html(main_data, output_path):
    """Generate the root HTML file"""
    html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Schoology Backup</title>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
    <h1>Schoology Backup</h1>
"""
    for section_id, section in main_data.items():
        html += f"    <h2>{section['course_title']} - {section['section_title']}</h2>\n    <a href='sections/{section_id}/section.html' class=\"button\">Go To Section</a>"
    html += """  </body>
</html>
"""
    # Write the HTML file
    with open(output_path, "w") as f:
        f.write(html)

def process_folder(folder, all_items, section_id):
    """Recursive function to process a folder and all its sub-items"""
    html = ""
    html += f"<details><summary>📁{colors_to_emojis[folder['color']]} {folder['title']}</summary><ul>\n"

    # Loop through the items
    for sub_item in folder['contents']:
        if (all_items.get(sub_item['id'], None) is None) and (sub_item['type'] != 'folder'):
            raw_item_data = get_item_data(sub_item['id'], section_id, sub_item['type'])
            section_path = sections_root / str(section_id)
            new_item = process_item(raw_item_data, sub_item['type'], section_path, section_id)
            all_items[new_item['id']] = new_item
        match sub_item['type']:
            case 'folder':
                html += "<li>"
                html += process_folder(sub_item, all_items, section_id)
                html += "</li>"
            case 'assignment':
                html += f'<li><a href="assignments/{sub_item["id"]}/assignment.html">📝 {all_items[sub_item["id"]]["title"]}</a></li>\n'
            case 'document':
                html += f'<li><a href="docs/{sub_item["id"]}/doc.html">📄 {all_items.get(sub_item["id"], {'title': 'Unknown Document'})["title"]}</a></li>\n'
            case 'page':
                html += f'<li><a href="pages/{sub_item["id"]}/page.html">📄 {all_items[sub_item["id"]]["title"]}</a></li>\n'
    html += "</ul></details>"
    return html

def generate_section_html_with_folders(section, output_path):
    """Generate the HTML for a specific section"""

    all_items = {}

    html = f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Schoology Backup - {section['course_title']}</title>
    <link rel="stylesheet" href="../../style.css">
  </head>
  <body>
    <h1>{section['course_title']} ({section['section_title']})</h1>
"""
    for assignment in section['assignments']:
        all_items[assignment['id']] = assignment
    
    for page in section['pages']:
        all_items[page['id']] = page
    
    for doc in section['documents']:
        all_items[doc['id']] = doc

    for item in section['root_folder']:
        if item['type'] == 'folder':
            html += process_folder(item, all_items, section['section_id'])
        elif item['type'] == 'assignment':
            html += f'<a href="assignments/{item["id"]}/assignment.html">📝 {all_items[item["id"]]["title"]}</a><br>\n'
        elif item['type'] == 'document':
            html += f'<a href="docs/{item["id"]}/doc.html">📄 {all_items[item["id"]]["title"]}</a><br>\n'
        elif item['type'] == 'page':
            html += f'<a href="pages/{item["id"]}/page.html">📄 {all_items[item["id"]]["title"]}</a><br>\n'

    html += """  </body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html)

def generate_attachments_html(data_item, heading_level = 2):
    """Generate the HTML for attachments"""

    internal_html = ""
    if any(key in data_item['attachments'] for key in ("videos", "links", "files")):
        internal_html += f"    <h{heading_level}>Attachments</h{heading_level}>\n"
        internal_html += ""
        if data_item['attachments'].get('files', None) is not None:
            internal_html += f"    <h{heading_level+1}>Files</h{heading_level+1}>\n    <ul>\n"
            for file in data_item['attachments']['files']:
                internal_html += f"        <li><a href='{file['path']}'>📄 {file['title']}</a></li>\n"
            internal_html += "    </ul>\n"
        if data_item['attachments'].get('links', None) is not None:
            internal_html += f"    <h{heading_level+1}>Links</h{heading_level+1}>\n    <ul>\n"
            for link in data_item['attachments']['links']:
                internal_html += f"        <li><a href='{link['url']}'>🔗 {link['title']}</a></li>\n"
            internal_html += "    </ul>\n"
        if data_item['attachments'].get('videos', None) is not None:
            internal_html += f"    <h{heading_level+1}>Videos</h{heading_level+1}>\n    <ul>\n"
            for video in data_item['attachments']['videos']:
                internal_html += f"        <li><a href='{video['url']}'>📽️ {video['title']}</a></li>\n"
            internal_html += "    </ul>\n"
    return internal_html

def generate_assignment_html(assignment, output_path):
    """Generate the HTML file for an attachment"""

    html = f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Schoology Backup - {assignment['title']}</title>
    <link rel="stylesheet" href="../../../../style.css">
  </head>
  <body>
    <h1>{assignment['title']}</h1>
    <h2>Due: {assignment['due']}</h2>
    <p>{assignment['description'].replace("\n", "<br>")}</p>
"""
    html += generate_attachments_html(assignment)
    if assignment['submissions'] is not None:
        html += "<h2>Submissions</h2>\n"
        for submission in assignment['submissions']:
            html += f"<h3>Revision {submission['revision_id']}</h3>\n"
            html += generate_attachments_html(submission, 4)
            
    html += """  </body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html)

def generate_document_html(doc, output_path):
    """Generate the HTML file for a document"""

    html = f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Schoology Backup - {doc['title']}</title>
    <link rel="stylesheet" href="../../../../style.css">
  </head>
  <body>
    <h1>{doc['title']}</h1>
"""
    html += generate_attachments_html(doc)
    html += """  </body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html)

def export_page(page, output_path):
    """Generate the HTML file for a page"""

    safe_body = ht.escape(page['body'])
    html = f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Schoology Backup - {page['title']}</title>
    <link rel="stylesheet" href="../../../../style.css">
  </head>
  <body>
    <h1>{page['title']}</h1>
    <code>{safe_body}</code>
"""
    html += generate_attachments_html(page)
    html += """  </body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html)

def process_attachments(dataobj, base_path, revision_id = None) -> dict:
    """Process the attachments for an item"""

    attachment_list = {}

    has_attachments = hasattr(dataobj, 'attachments') and dataobj.attachments is not None
    if has_attachments:
        mkdir_if_not_exists(f'{base_path}/attachments')
        if "files" in dataobj.attachments:
            mkdir_if_not_exists(f'{base_path}/attachments/files')
            for file in dataobj.attachments['files']['file']:
                if file.get('converted_status', '4') == '1' and args.converted:
                    file_data = sc.get_file(file.get('converted_download_path'))
                    file_path = f"attachments/files/{file.get('id')}.{file.get('converted_extension')}" if revision_id is None else f"submissions/{revision_id}/attachments/files/{file.get('id')}.{file.get('converted_extension')}"
                    Path(file_path).parent.mkdir(exist_ok=True, parents=True)
                    with open(f"{base_path}/{file_path}", 'wb') as f:
                        f.write(file_data.content)
                else:
                    file_data = sc.get_file(file.get('download_path'))
                    file_path = f"attachments/files/{file.get('id')}.{file.get('extension')}" if revision_id is None else f"submissions/{revision_id}/attachments/files/{file.get('id')}.{file.get('extension')}"
                    Path(base_path / file_path).parent.mkdir(exist_ok=True, parents=True)
                    with open(f"{base_path}/{file_path}", 'wb') as f:
                        f.write(file_data.content)
                
                attachment_list.setdefault('files', []).append({
                    'id': file.get('id'),
                    'title': file.get('title'),
                    'file_name': file.get('filename'),
                    'md5sum': file.get('md5_checksum'),
                    'path': file_path
                })
        if "links" in dataobj.attachments:
            mkdir_if_not_exists(f'{base_path}/attachments/links')
            for link in dataobj.attachments['links']['link']:
                attachment_list.setdefault('links', []).append({
                    'id': link.get('id'),
                    'title': link.get('title'),
                    'url': link.get('url')
                })
                with open(f"{base_path}/attachments/links/{link.get('id')}.linktxt", 'w') as f:
                    f.write(link.get('url'))
        if "videos" in dataobj.attachments:
            mkdir_if_not_exists(f'{base_path}/attachments/videos')
            for video in dataobj.attachments['videos']['video']:
                attachment_list.setdefault('videos', []).append({
                    'id': video.get('id'),
                    'title': video.get('title'),
                    'url': video.get('url'),
                })
                with open(f"{base_path}/attachments/videos/{video.get('id')}.videolink", 'w') as f:
                    f.write(video.get('url'))
    return attachment_list

def handle_subfolder(item, section_id) -> dict:
    """Recursive function to handle folders inside of folders"""

    subfolder = sc.get_section_folder(section_id, item.get('id'))
    folder_contents = []
    for sub_item in getattr(subfolder, 'folder-item'):
        if sub_item['type'] == 'folder':
            folder_contents.append(handle_subfolder(sub_item, section_id))
        else:
            folder_contents.append({
                'id': sub_item['id'],
                'type': sub_item['type']
            })
    folder_data = {
        'id': item.get('id'),
        'title': item.get('title'),
        'type': 'folder',
        'body': item.get('body'),
        'color': item.get('color', 'blue'),
        'contents': folder_contents,
    }

    return folder_data

def process_item(item_data, item_type, section_path, section_id):
    """Process an item, download all its attachments and details"""

    match item_type:
        case 'assignment':
            assignment_path = Path.joinpath(section_path, 'assignments', str(item_data.id))
            mkdir_if_not_exists(assignment_path)
            attachments = process_attachments(item_data, assignment_path)
            submissions = sc.get_assignment_submissions(section_id, assignment.id)
            if len(submissions) > 0:
                submission_list = []
                filtered_submissions = [x for x in submissions if x.uid == me.id]
                for submission in filtered_submissions:
                    submission_attachments = process_attachments(submission, assignment_path, revision_id=submission.revision_id)
                    submission_list.append({
                        "created": submission.created,
                        "draft": bool(submission.draft),
                        "late": bool(submission.late),
                        "revision_id": submission.revision_id,
                        "num_items": submission.num_items,
                        "attachments": submission_attachments
                    })
            assignment_data = {
                'id': assignment.id,
                'folder_id': assignment.folder_id,
                'grading': {
                    'grading_scale': assignment.grading_scale,
                    'grading_period': assignment.grading_period,
                    'grading_category': assignment.grading_category,
                    'max_points': assignment.max_points,
                    'grade_stats': assignment.grade_stats,
                },
                'title': assignment.title,
                'description': assignment.description,
                'due': assignment.due,
                'web_url': assignment.web_url,
                'attachments': attachments,
                'submissions': submission_list if len(submissions) > 0 else None
            }
            main_data[section_id]['assignments'].append(assignment_data)
            generate_assignment_html(assignment_data, f"{assignment_path}/assignment.html")
            return assignment_data
        case 'document':
            doc_path = Path.joinpath(section_path, 'docs', str(item_data.id))
            mkdir_if_not_exists(doc_path)
            attachments = process_attachments(item_data, doc_path)
            doc_data = {
                'id': item_data.id,
                'folder_id': item_data.course_fid,
                'title': item_data.title,
                'attachments': attachments
            }
            main_data[section_id]['documents'].append(doc_data)
            generate_document_html(doc_data, f"{doc_path}/doc.html")
            return doc_data
        case 'page':
            page_path = Path.joinpath(section_path, 'pages', str(item_data.id))
            mkdir_if_not_exists(page_path)
            attachments = process_attachments(item_data, page_path)
            page_data = {
                'id': item_data.id,
                'folder_id': item_data.folder_id,
                'title': item_data.title,
                'body': item_data.body,
                'attachments': attachments
            }
            main_data[section_id]['pages'].append(page_data)
            export_page(page_data, f"{page_path}/page.html")
            return page_data

if __name__ == '__main__':
    # Authenticate With Schoology
    sc = schoolopy.Schoology(schoolopy.Auth(config['key'], config['secret']))
    sc.limit = config['limit']

    # Get the current user's data
    me = sc.get_me()
    sections = sc.get_user_sections(me.id)
    if len(sections) <= 0:
        exit("No sections found! Exiting...")

    # Loop through each section that the user is in
    with tqdm(total=len(sections), desc="Processing Sections") as pbar:
        for idx, section in enumerate(sections):
            # Initialize the main datastore
            main_data[section.id] = {
                'course_title': section.course_title,
                'course_id': section.course_id,
                'section_id': section.id,
                'section_title': section.section_title,
                'documents': [],
                'assignments': [],
                'pages': [],
                'root_folder': []
            }
            
            # Prepare and initialize paths for data
            section_path = sections_root / str(section.id)
            section_path.mkdir(exist_ok=True)
            (section_path/ 'assignments').mkdir(exist_ok=True)
            (section_path/ 'docs').mkdir(exist_ok=True)
            (section_path/ 'pages').mkdir(exist_ok=True)

            # Loop through all the assignments in the current section
            assignments = sc.get_assignments(section.id, with_attachments=True)
            with tqdm(total=len(assignments), desc=f"Processing Assignments for {section.course_title}") as apbar:
                for assignment in assignments:
                    process_item(assignment, 'assignment', section_path, section.id)
                    apbar.update(1)
            
            # Loop through all the documents in the current section
            docs = sc.get_section_documents(section.id)
            with tqdm(total=len(docs), desc=f"Processing Documents for {section.course_title}") as dpbar:
                for doc in docs:
                    process_item(doc, 'document', section_path, section.id)
                    dpbar.update(1)
            
            # Loop through all the pages in the current section
            pages = sc.get_pages(section.id, True)
            with tqdm(total=len(pages), desc=f"Processing Pages for {section.course_title}") as ppbar:
                for page in pages:
                    process_item(page, 'page', section_path, section.id)
                    dpbar.update(1)

            # Loop through all the folders and subfolders in the current section
            section_root_folder = sc.get_section_folder(section.id, 0)
            with tqdm(total=len(getattr(section_root_folder, 'folder-item')), desc=f"Processing Folders for {section.course_title}") as fpbar:
                for item in getattr(section_root_folder, 'folder-item'):
                    if item.get('type') == 'folder':
                        folder_data = handle_subfolder(item, section.id)
                        main_data[section.id]['root_folder'].append(folder_data)
                    else:
                        main_data[section.id]['root_folder'].append({
                            'id': item.get('id'),
                            'type': item.get('type')
                        })
                    fpbar.update(1)

            # Export the HTML file for this section
            generate_section_html_with_folders(main_data[section.id], f'{section_path}/section.html')
            # Update the progress bar
            pbar.update(1)

    # Generate the main HTML file
    generate_html(main_data, Path.joinpath(root_path, 'index.html'))

    # Save the data store to a JSON file in the data path
    with open(Path.joinpath(root_path, 'schoology_data.json'), 'w') as f:
        json.dump(main_data, f, indent=4)

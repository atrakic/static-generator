#!/usr/bin/env python3

"""Make static website/blog with Python."""

import argparse
import os
import shutil
import re
import glob
import sys
import json
import datetime
import markdown
from urllib.parse import urlsplit


DEFAULT_PARAMS = {
    "subtitle": "Lorem Ipsum",
    "author": "admin",
    "site_url": "http://localhost",
    "current_year": datetime.datetime.now().year,
    "site_dir": "_site",
    "static_dir": "static",
    "content_dir": "content",
    "layout_dir": "layout",
    "sections": [
        {"slug": "blog", "glob": "*.md", "title": "Blog", "enabled": True},
        {"slug": "news", "glob": "*.html", "title": "News", "enabled": False},
    ],
    "nav_pages": [
        {"slug": "contact", "title": "Contact"},
        {"slug": "about", "title": "About"},
    ],
}


CLI_PARAM_NAMES = (
    "subtitle",
    "author",
    "site_url",
    "site_dir",
    "static_dir",
    "content_dir",
    "layout_dir",
)


def add_build_arguments(parser):
    """Add build-related CLI arguments to a parser."""
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to JSON config file (default: %(default)s)",
    )
    parser.add_argument("--subtitle", help="Site subtitle")
    parser.add_argument("--author", help="Default author name")
    parser.add_argument("--site-url", dest="site_url", help="Public site URL")
    parser.add_argument("--site-dir", dest="site_dir", help="Output directory")
    parser.add_argument(
        "--static-dir", dest="static_dir", help="Static assets directory"
    )
    parser.add_argument(
        "--content-dir", dest="content_dir", help="Content source directory"
    )
    parser.add_argument(
        "--layout-dir", dest="layout_dir", help="Layout templates directory"
    )
    parser.add_argument(
        "--sections",
        help="Comma-separated list of section slugs to enable (e.g. blog,news)",
    )


def fread(filename):
    """Read file and close the file."""
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def fwrite(filename, text):
    """Write content to file and close the file."""
    basedir = os.path.dirname(filename)
    if not os.path.isdir(basedir):
        os.makedirs(basedir)

    with open(filename, "w", encoding="utf-8") as file:
        file.write(text)


def log(msg, *args):
    """Log message with specified arguments."""
    sys.stderr.write(msg.format(*args) + "\n")


def truncate(text, words=25):
    """Remove tags and truncate text to the specified number of words."""
    return " ".join(re.sub("(?s)<.*?>", " ", text).split()[:words])


def read_headers(text):
    """Parse headers in text and yield (key, value, end-index) tuples."""
    for match in re.finditer(r"\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*|.+", text):
        if not match.group(1):
            break
        yield match.group(1), match.group(2), match.end()


def rfc_2822_format(date_str):
    """Convert yyyy-mm-dd date string to RFC 2822 format date string."""
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%a, %d %b %Y %H:%M:%S +0000")


def read_content(filename):
    """Read content and metadata from file into a dictionary."""
    # Read file content.
    text = fread(filename)

    # Read metadata and save it in a dictionary.
    date_slug = os.path.basename(filename).split(".")[0]
    match = re.search(r"^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$", date_slug)
    content = {
        "date": match.group(1) or "1970-01-01",
        "slug": match.group(2),
    }

    # Read headers.
    end = 0
    for key, val, end in read_headers(text):
        content[key] = val

    # Separate content from headers.
    text = text[end:]

    # Convert Markdown content to HTML.
    if filename.endswith((".md", ".mkd", ".mkdn", ".mdown", ".markdown")):
        try:
            if _test == "ImportError":
                raise ImportError("Error forced by test")
            text = markdown.markdown(text, extensions=["tables"]) + "\n"
        except ImportError as err:
            log("WARNING: Cannot render Markdown in {}: {}", filename, str(err))

    # Update the dictionary with content and RFC 2822 date.
    content.update({"content": text, "rfc_2822_date": rfc_2822_format(content["date"])})

    return content


def render(template, **params):
    """Replace placeholders in template with values from params."""
    return re.sub(
        r"{{\s*([^}\s]+)\s*}}",
        lambda match: str(params.get(match.group(1), match.group(0))),
        template,
    )


def make_pages(src, dst, layout, **params):
    """Generate pages from page content."""
    items = []

    for src_path in glob.glob(src):
        content = read_content(src_path)

        page_params = dict(params, **content)

        # Populate placeholders in content if content-rendering is enabled.
        if page_params.get("render") == "yes":
            rendered_content = render(page_params["content"], **page_params)
            page_params["content"] = rendered_content
            content["content"] = rendered_content

        items.append(content)

        dst_path = render(dst, **page_params)
        output = render(layout, **page_params)

        log("Rendering {} => {} ...", src_path, dst_path)
        fwrite(dst_path, output)

    return sorted(items, key=lambda x: x["date"], reverse=True)


def make_list(posts, dst, list_layout, item_layout, **params):
    """Generate list page for a blog."""
    items = []
    for post in posts:
        item_params = dict(params, **post)
        item_params["summary"] = truncate(post["content"])
        item = render(item_layout, **item_params)
        items.append(item)

    params["content"] = "".join(items)
    dst_path = render(dst, **params)
    output = render(list_layout, **params)

    log("Rendering list => {} ...", dst_path)
    fwrite(dst_path, output)


def build_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate a static site from content and layout files.",
    )
    subparsers = parser.add_subparsers(dest="command")

    build_cmd = subparsers.add_parser("build", help="Generate the static site")
    add_build_arguments(build_cmd)

    clean_cmd = subparsers.add_parser(
        "clean", help="Remove the generated site directory"
    )
    clean_cmd.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to JSON config file (default: %(default)s)",
    )
    clean_cmd.add_argument(
        "--site-dir", dest="site_dir", help="Output directory to remove"
    )
    return parser


def load_params(config_path="config.json"):
    """Load params from defaults and an optional JSON config file."""
    params = dict(DEFAULT_PARAMS)
    if config_path and os.path.isfile(config_path):
        params.update(json.loads(fread(config_path)))
    return params


def normalize_params(params):
    """Normalize derived parameters for rendering."""
    normalized = dict(params)

    # Keep config simple: allow using only site_url.
    # If base_path is omitted, derive it from site_url path (e.g. /my-site).
    if (
        "base_path" not in normalized or normalized["base_path"] == ""
    ) and normalized.get("site_url"):
        base_path = urlsplit(normalized["site_url"]).path.rstrip("/")
        normalized["base_path"] = base_path

    # Backward-compatible fallback: if site_url is missing, build it from base_path.
    if not normalized.get("site_url"):
        normalized["site_url"] = "http://localhost" + normalized.get("base_path", "")

    return normalized


def build_site(params):
    """Render the site using the supplied parameters."""
    params = normalize_params(params)

    site_dir = params["site_dir"]
    static_dir = params["static_dir"]
    content_dir = params["content_dir"]
    layout_dir = params["layout_dir"]

    # Build nav_links from enabled sections + configured static pages
    base_path = params.get("base_path", "")
    nav_parts = [
        f'<a class="nav-link" href="{base_path}/{s["slug"]}/">{s["title"]}</a>'
        for s in params.get("sections", [])
        if s.get("enabled", True)
    ] + [
        f'<a class="nav-link" href="{base_path}/{p["slug"]}/">{p["title"]}</a>'
        for p in params.get("nav_pages", [])
    ]
    params["nav_links"] = "\n                    ".join(nav_parts)

    # Create a new _site directory from scratch
    if os.path.isdir(site_dir):
        shutil.rmtree(site_dir)
    shutil.copytree(static_dir, site_dir)

    # Load layouts
    page_layout = fread(os.path.join(layout_dir, "page.html"))
    post_layout = fread(os.path.join(layout_dir, "post.html"))
    list_layout = fread(os.path.join(layout_dir, "list.html"))
    item_layout = fread(os.path.join(layout_dir, "item.html"))
    feed_xml = fread(os.path.join(layout_dir, "feed.xml"))
    item_xml = fread(os.path.join(layout_dir, "item.xml"))

    # Combine layouts to form final layouts.
    post_layout = render(page_layout, content=post_layout)
    list_layout = render(page_layout, content=list_layout)

    # Create site pages.
    make_pages(
        os.path.join(content_dir, "_index.html"),
        os.path.join(site_dir, "index.html"),
        page_layout,
        **params,
    )
    make_pages(
        os.path.join(content_dir, "[!_]*.html"),
        os.path.join(site_dir, "{{ slug }}", "index.html"),
        page_layout,
        **params,
    )

    # Create sections (blogs, news, etc.)
    for section in params.get("sections", []):
        if not section.get("enabled", True):
            continue
        slug = section["slug"]
        title = section.get("title", slug.capitalize())
        content_glob = section.get("glob", "*.html")
        posts = make_pages(
            os.path.join(content_dir, slug, content_glob),
            os.path.join(site_dir, slug, "{{ slug }}", "index.html"),
            post_layout,
            blog=slug,
            **params,
        )
        make_list(
            posts,
            os.path.join(site_dir, slug, "index.html"),
            list_layout,
            item_layout,
            blog=slug,
            title=title,
            **params,
        )
        make_list(
            posts,
            os.path.join(site_dir, slug, "rss.xml"),
            feed_xml,
            item_xml,
            blog=slug,
            title=title,
            **params,
        )


def clean_site(params):
    """Remove generated site output if it exists."""
    site_dir = normalize_params(params)["site_dir"]
    if os.path.isdir(site_dir):
        shutil.rmtree(site_dir)
        log("Removed {}", site_dir)
    else:
        log("Nothing to remove at {}", site_dir)


def parse_args(argv):
    """Parse CLI arguments, defaulting to the build command."""
    argv = list(argv)

    help_flags = {"-h", "--help"}
    if argv and argv[0] in help_flags:
        build_parser().print_help()
        raise SystemExit(0)
    if not argv or argv[0].startswith("-"):
        argv = ["build"] + argv

    return build_parser().parse_args(argv)


def main(argv=None):
    """CLI entrypoint."""
    if argv is None:
        argv = []
    args = parse_args(argv)
    params = load_params(args.config)

    if getattr(args, "site_dir", None) is not None:
        params["site_dir"] = args.site_dir

    if args.command == "clean":
        clean_site(params)
        return 0

    for key in CLI_PARAM_NAMES:
        value = getattr(args, key)
        if value is not None:
            params[key] = value

    # --sections blog,news enables only the named slugs
    if getattr(args, "sections", None) is not None:
        enabled = set(args.sections.split(","))
        for section in params.get("sections", []):
            section["enabled"] = section["slug"] in enabled

    build_site(params)
    return 0


# Test parameter to be set temporarily by unit tests.
_test = None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

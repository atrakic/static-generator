import unittest
import makesite
import os
import shutil
import json

from tests import path


class MainTest(unittest.TestCase):
    def setUp(self):
        path.move("_site", "_site.backup")
        path.move("config.json", "config.json.backup")

    def tearDown(self):
        path.move("_site.backup", "_site")
        path.move("config.json.backup", "config.json")

    def test_site_missing(self):
        makesite.main()

    def test_site_exists(self):
        os.mkdir("_site")
        with open("_site/foo.txt", "w") as f:
            f.write("foo")

        self.assertTrue(os.path.isfile("_site/foo.txt"))
        makesite.main()
        self.assertFalse(os.path.isfile("_site/foo.txt"))

    def test_default_params(self):
        makesite.main()

        with open("_site/blog/proin-quam/index.html") as f:
            s1 = f.read()

        with open("_site/blog/rss.xml") as f:
            s2 = f.read()

        shutil.rmtree("_site")

        self.assertIn('href="/">Home</a>', s1)
        self.assertIn("<title>Proin Quam - Lorem Ipsum</title>", s1)
        self.assertIn("Published on 2018-01-01 by <b>admin</b>", s1)

        self.assertIn("<link>http://localhost/</link>", s2)
        self.assertIn("<link>http://localhost/blog/proin-quam/</link>", s2)

    def test_json_params(self):
        params = {
            "subtitle": "Foo",
            "author": "Bar",
            "site_url": "http://localhost/base",
        }
        with open("config.json", "w") as f:
            json.dump(params, f)
        makesite.main()

        with open("_site/blog/proin-quam/index.html") as f:
            s1 = f.read()

        with open("_site/blog/rss.xml") as f:
            s2 = f.read()

        shutil.rmtree("_site")

        self.assertIn('href="/base/">Home</a>', s1)
        self.assertIn("<title>Proin Quam - Foo</title>", s1)
        self.assertIn("Published on 2018-01-01 by <b>Bar</b>", s1)

        self.assertIn("<link>http://localhost/base/</link>", s2)
        self.assertIn("<link>http://localhost/base/blog/proin-quam/</link>", s2)

    def test_cli_args_override_params(self):
        makesite.main(
            ["build", "--site-url", "http://localhost/cli", "--author", "CLI"]
        )

        with open("_site/blog/proin-quam/index.html") as f:
            s1 = f.read()

        with open("_site/blog/rss.xml") as f:
            s2 = f.read()

        shutil.rmtree("_site")

        self.assertIn('href="/cli/">Home</a>', s1)
        self.assertIn("Published on 2018-01-01 by <b>CLI</b>", s1)
        self.assertIn("<link>http://localhost/cli/</link>", s2)

    def test_clean_subcommand(self):
        os.mkdir("_site")
        with open("_site/foo.txt", "w") as f:
            f.write("foo")

        makesite.main(["clean"])

        self.assertFalse(os.path.exists("_site"))

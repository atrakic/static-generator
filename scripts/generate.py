#!/usr/bin/env python3

""" Generate markdown contents"""
from faker import Faker
from mdgen import MarkdownPostProvider


def build_post_with_title(fake):
	"""Build a markdown post prefixed with a makesite title header."""
	title = fake.sentence(nb_words=5).rstrip('.')
	post = fake.post(size="medium")
	return f"<!-- title: {title} -->\n\n{post}"


fake = Faker()
fake.add_provider(MarkdownPostProvider)
fake_post = build_post_with_title(fake)
print(fake_post)

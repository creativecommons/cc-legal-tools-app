#!/bin/sh
pandoc techspec.md --to pdf -V links-as-notes -o techspec.pdf --standalone

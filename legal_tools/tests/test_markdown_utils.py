# Third-party
from django.test import SimpleTestCase

# First-party/Local
from legal_tools.markdown_utils import legal_code_html_to_markdown


class MarkdownUtilsTest(SimpleTestCase):
    def test_legal_code_html_to_markdown(self):
        html = """
        <main>
          <div id="legal-code-body">
            <h2>Attribution 4.0 International</h2>
            <p>
              <span style="text-decoration: underline;">Adapted Material</span>
              means material described in <a href="#s1">Section 1</a>.
            </p>
            <ol type="a">
              <li>First item</li>
              <li>
                Second item
                <ol type="i">
                  <li>Nested item</li>
                  <li>Second nested item</li>
                </ol>
              </li>
            </ol>
          </div>
        </main>
        """
        expected = (
            "## Attribution 4.0 International\n\n"
            "<u>Adapted Material</u> means material described in "
            "[Section 1](#s1).\n\n"
            '<ol type="a">\n'
            "  <li>First item</li>\n"
            "  <li>\n"
            "    Second item\n"
            '    <ol type="i">\n'
            "      <li>Nested item</li>\n"
            "      <li>Second nested item</li>\n"
            "    </ol>\n"
            "  </li>\n"
            "</ol>\n"
        )

        self.assertEqual(expected, legal_code_html_to_markdown(html))

    def test_legal_code_html_to_markdown_heading_levels(self):
        html = """
        <div id="legal-code-body">
          <h1>Title</h1>
          <h2>Section</h2>
          <h3>Subsection</h3>
        </div>
        """

        self.assertEqual(
            "# Title\n\n## Section\n\n### Subsection\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_normalizes_base_less_links(self):
        html = """
        <div id="legal-code-body">
          <p><a href="/policies/">policies</a></p>
          <p>
            <a href="//creativecommons.org/compatiblelicenses">
            compatible licenses</a>
          </p>
        </div>
        """

        self.assertEqual(
            "[policies](https://creativecommons.org/policies/)\n\n"
            "[compatible licenses]"
            "(https://creativecommons.org/compatiblelicenses)\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_preserves_absolute_link_parts(self):
        html = """
        <div id="legal-code-body">
          <p>
            <a href="https://example.test/path/?x=1#part">details</a>
          </p>
        </div>
        """

        self.assertEqual(
            "[details](https://example.test/path/?x=1#part)\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_escapes_link_syntax(self):
        html = """
        <div id="legal-code-body">
          <p>
            <a href="/policies/some path(1)">Policy [draft]</a>
          </p>
        </div>
        """

        self.assertEqual(
            "[Policy \\[draft\\]]"
            "(<https://creativecommons.org/policies/some path(1)>)\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_uppercase_list_and_emphasis(self):
        html = """
        <div id="legal-code-body">
          <ol type="A">
            <li>
              <strong>Notice</strong> and <em>care</em> must be retained.
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            '<ol type="A">\n'
            "  <li><strong>Notice</strong> and <em>care</em> must be "
            "retained.</li>\n"
            "</ol>\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_decimal_list(self):
        html = """
        <div id="legal-code-body">
          <ol>
            <li>First decimal item.</li>
            <li>Second decimal item.</li>
          </ol>
        </div>
        """

        self.assertEqual(
            "1. First decimal item.\n"
            "2. Second decimal item.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_unwraps_div_in_decimal_list(self):
        html = """
        <div id="legal-code-body">
          <ol>
            <li>
              <div class="padding-left-normal">
                <strong>Term</strong> means something.
              </div>
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            "1. **Term** means something.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_unordered_list(self):
        html = """
        <div id="legal-code-body">
          <ul>
            <li>First bullet.</li>
            <li>Second bullet.</li>
          </ul>
        </div>
        """

        self.assertEqual(
            "- First bullet.\n"
            "- Second bullet.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_ordered_list_start(self):
        html = """
        <div id="legal-code-body">
          <ol start="3">
            <li>Third decimal item.</li>
            <li>Fourth decimal item.</li>
          </ol>
        </div>
        """

        self.assertEqual(
            "3. Third decimal item.\n"
            "4. Fourth decimal item.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_wraps_paragraphs(self):
        text = (
            "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda "
            "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega."
        )
        html = f"""
        <div id="legal-code-body">
          <p>{text}</p>
        </div>
        """

        markdown = legal_code_html_to_markdown(html)
        lines = markdown.splitlines()

        self.assertGreater(len(lines), 1)
        self.assertEqual(text, " ".join(lines))
        self.assertTrue(all(len(line) <= 71 for line in lines))

    def test_legal_code_html_to_markdown_wraps_direct_text_nodes(self):
        text = (
            "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda "
            "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega."
        )
        html = f"""
        <div id="legal-code-body">
          <h2>Notice</h2>
          {text}
        </div>
        """

        markdown = legal_code_html_to_markdown(html)
        lines = markdown.splitlines()

        self.assertEqual("## Notice", lines[0])
        self.assertEqual(text, " ".join(lines[2:]))
        self.assertTrue(all(len(line) <= 71 for line in lines))

    def test_legal_code_html_to_markdown_wraps_markdown_emphasis(self):
        html = """
        <div id="legal-code-body">
          <p>
            Alpha <strong>strong emphasis</strong> and <em>emphasis
            text</em> continue through enough words to require wrapping in
            generated Markdown output.
          </p>
        </div>
        """

        markdown = legal_code_html_to_markdown(html)

        self.assertIn("**strong emphasis**", markdown)
        self.assertIn("*emphasis text*", markdown)
        self.assertTrue(all(len(line) <= 71 for line in markdown.splitlines()))

    def test_legal_code_html_to_markdown_normalizes_links_in_html_lists(self):
        html = """
        <div id="legal-code-body">
          <ol type="a">
            <li><a href="/policies/">policies</a></li>
          </ol>
        </div>
        """

        self.assertEqual(
            '<ol type="a">\n'
            '  <li><a href="https://creativecommons.org/policies/">'
            "policies</a></li>\n"
            "</ol>\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_wraps_html_list_items(self):
        text = (
            "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda "
            "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega."
        )
        html = f"""
        <div id="legal-code-body">
          <ol type="a">
            <li>{text}</li>
          </ol>
        </div>
        """

        markdown = legal_code_html_to_markdown(html)
        lines = markdown.splitlines()

        self.assertEqual('<ol type="a">', lines[0])
        self.assertEqual("  <li>", lines[1])
        self.assertEqual("  </li>", lines[-2])
        self.assertEqual("</ol>", lines[-1])
        self.assertNotIn("", lines)
        self.assertEqual(text, " ".join(line.strip() for line in lines[2:-2]))
        self.assertTrue(all(line.startswith("    ") for line in lines[2:-2]))
        self.assertTrue(all(len(line) <= 71 for line in lines))

    def test_legal_code_html_to_markdown_wraps_html_block_tags(self):
        text = (
            "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda "
            "mu nu xi omicron pi rho sigma tau."
        )
        html = f"""
        <div id="legal-code-body">
          <ol type="a">
            <li><p>{text}</p></li>
          </ol>
        </div>
        """

        markdown = legal_code_html_to_markdown(html)
        lines = markdown.splitlines()

        self.assertIn("    <p>", lines)
        self.assertIn("    </p>", lines)
        self.assertTrue(all(len(line) <= 71 for line in lines))

    def test_legal_code_html_to_markdown_unwraps_div_in_html_list(self):
        html = """
        <div id="legal-code-body">
          <ol type="a">
            <li>
              <div class="padding-left-normal">
                <strong>Term</strong> means something.
              </div>
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            '<ol type="a">\n'
            "  <li><strong>Term</strong> means something.</li>\n"
            "</ol>\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_unwraps_div_around_blocks(self):
        html = """
        <div id="legal-code-body">
          <ol type="a">
            <li>
              <div class="padding-left-normal">
                <p>Introductory paragraph.</p>
                <ol type="i">
                  <li>Nested item.</li>
                </ol>
              </div>
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            '<ol type="a">\n'
            "  <li>\n"
            "    <p>Introductory paragraph.</p>\n"
            '    <ol type="i">\n'
            "      <li>Nested item.</li>\n"
            "    </ol>\n"
            "  </li>\n"
            "</ol>\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_preserves_long_tokens(self):
        token = f"https://creativecommons.org/{'licensepath' * 9}"
        html = f"""
        <div id="legal-code-body">
          <p>{token}</p>
        </div>
        """

        markdown = legal_code_html_to_markdown(html)

        self.assertEqual(f"{token}\n", markdown)
        self.assertGreater(len(markdown.splitlines()[0]), 70)

    def test_legal_code_html_to_markdown_uses_document_root(self):
        html = """
        <div id="legal-code-document">
          <h1>Document Title</h1>
          <div id="legal-code-body">
            <h2>Body Title</h2>
            <p>Legal code body.</p>
          </div>
          <p>After legal code.</p>
        </div>
        """

        self.assertEqual(
            "# Document Title\n\n"
            "## Body Title\n\n"
            "Legal code body.\n\n"
            "After legal code.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_nested_decimal_list(self):
        html = """
        <div id="legal-code-body">
          <ol type="a">
            <li>
              Parent item
              <ol>
                <li>Nested decimal item.</li>
                <li>Second nested decimal item.</li>
              </ol>
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            '<ol type="a">\n'
            "  <li>\n"
            "    Parent item\n"
            "    <ol>\n"
            "      <li>Nested decimal item.</li>\n"
            "      <li>Second nested decimal item.</li>\n"
            "    </ol>\n"
            "  </li>\n"
            "</ol>\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_native_nested_decimal_list(self):
        html = """
        <div id="legal-code-body">
          <ol>
            <li>
              Parent item
              <ol>
                <li>Nested decimal item.</li>
                <li>Second nested decimal item.</li>
              </ol>
            </li>
          </ol>
        </div>
        """

        self.assertEqual(
            "1. Parent item\n"
            "   1. Nested decimal item.\n"
            "   2. Second nested decimal item.\n",
            legal_code_html_to_markdown(html),
        )

    def test_legal_code_html_to_markdown_html_list_inside_native_list(self):
        html = """
        <div id="legal-code-body">
          <ul>
            <li>
              Parent item
              <ol type="a">
                <li>Nested alpha item.</li>
              </ol>
            </li>
          </ul>
        </div>
        """

        self.assertEqual(
            "- Parent item\n"
            '  <ol type="a">\n'
            "    <li>Nested alpha item.</li>\n"
            "  </ol>\n",
            legal_code_html_to_markdown(html),
        )

Embedding widgets
====================

Member
------

If you have a site or a blog that mentions MKs name you need to add 
only one line to your template to get a popup with the latest oknesset data
for all the MKs mentioned ona page. Just before the </body> tag at the bottom
of the template add the line::

.. code-block:: html

    <script type="text/javascript" src="//oknesset.org/static/js/tooltip.js"></script>
    <script> generateMkFrameSet('#article'); </script>

replace `#article` with a jQuery selector that returns all the text elements.
To see a demo of a page using the Member widget visit https://oknesset.org/static/html/demo-article.html.

To embed a single Knesset member's card, use:

.. code-block:: html

    <iframe width="400" height="186" scrolling="no" style="border:0" src="https://oknesset.org/member/[member_id]/embed/"></iframe>

Replace `member_id` with the id of the member from the url, e.g:

You can get the embedding code for the member's page. For example visit
https://oknesset.org/member/885/, and click the `"עמבד"` button.

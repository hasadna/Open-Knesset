from django import template

from auxiliary.forms import TagSuggestionForm

register = template.Library()


class TagFormNode(template.Node):
    "Adds the tag suggestion into context"

    def render(self, context):
        forms = context.get('suggestion_forms', {})
        forms['tag'] = TagSuggestionForm()
        context['suggestion_forms'] = forms
        return ''

def do_add_tag_suggestion_form(parser, token):
    return TagFormNode()


register.tag('add_tag_suggestion_form', do_add_tag_suggestion_form)

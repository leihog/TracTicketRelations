import re

from pkg_resources import resource_filename
from genshi.builder import tag

from trac.core import *
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_script
from trac.ticket.api import ITicketManipulator
from trac.ticket.model import Ticket
from trac.resource import ResourceNotFound
from trac.util.text import shorten_line
from trac.util.compat import set, sorted

from model import TicketLinks, extract_ticket_ids

class TicketRelationsModule(Component):
    
    implements(IRequestFilter, ITemplateStreamFilter, ITemplateProvider, ITicketManipulator)
    
    fields = set(['blocking', 'blockedby'])

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if req.path_info.startswith('/ticket/'):
            # In case of an invalid ticket, the data is invalid
            if not data:
                return template, data, content_type

            tkt = data['ticket']
            links = TicketLinks(self.env, tkt)            
            for i in links.blocked_by:
                if Ticket(self.env, i)['status'] != 'closed':
                    add_script(req, 'ticketrelations/disable_resolve.js')
                    break

            for change in data.get('changes', {}):
                if not change.has_key('fields'):
                    continue
                for field, field_data in change['fields'].iteritems():
                    if field in self.fields:
                        if field_data['new'].strip():
                            new = extract_ticket_ids(field_data['new'])
                        else:
                            new = set()
                        if field_data['old'].strip():
                            old = extract_ticket_ids(field_data['old'])
                        else:
                            old = set()
                        add = new - old
                        sub = old - new
                        elms = tag()
                        if add:
                            elms.append(
                                tag.em(u', '.join([unicode(n) for n in sorted(add)]))
                            )
                            elms.append(u' added')
                        if add and sub:
                            elms.append(u'; ')
                        if sub:
                            elms.append(
                                tag.em(u', '.join([unicode(n) for n in sorted(sub)]))
                            )
                            elms.append(u' removed')
                        field_data['rendered'] = elms

        return template, data, content_type

    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        if not data:
            return stream

        # We try all at the same time to maybe catch also changed or processed templates
        if filename in ["report_view.html", "query_results.html", "ticket.html", "query.html"]:
            # For ticket.html
            if 'fields' in data and isinstance(data['fields'], list):
                for field in data['fields']:
                    for f in self.fields:
                        if field['name'] == f and data['ticket'][f]:
                            field['rendered'] = self._link_tickets(req, data['ticket'][f])
            # For query_results.html and query.html
            if 'groups' in data and isinstance(data['groups'], list):
                for group, tickets in data['groups']:
                    for ticket in tickets:
                        for f in self.fields:
                            if f in ticket:
                                ticket[f] = self._link_tickets(req, ticket[f])
            # For report_view.html
            if 'row_groups' in data and isinstance(data['row_groups'], list):
                for group, rows in data['row_groups']:
                    for row in rows:
                        if 'cell_groups' in row and isinstance(row['cell_groups'], list):
                            for cells in row['cell_groups']:
                                for cell in cells:
                                    # If the user names column in the report differently (blockedby AS "blocked by") then this will not find it
                                    if cell.get('header', {}).get('col') in self.fields:
                                        cell['value'] = self._link_tickets(req, cell['value'])
        return stream
        
    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        if req.args.get('action') == 'resolve' and req.args.get('action_resolve_resolve_resolution') == 'fixed':
            links = TicketLinks(self.env, ticket)
            for i in links.blocked_by:
                if Ticket(self.env, i)['status'] != 'closed':
                    yield None, 'Ticket #%s is blocking this ticket'%i

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        """Return the absolute path of a directory containing additional static resources (such as images, style sheets, etc). """
        return [('ticketrelations', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        pass

    def _link_tickets(self, req, tickets):
        items = []

        for i, word in enumerate(re.split(r'([;,\s]+)', re.sub('#', '', tickets))):
            if i % 2:
                items.append(word)
            elif word:
                ticketid = word
                word = '#%s' % word

                try:
                    ticket = Ticket(self.env, ticketid)
                    if 'TICKET_VIEW' in req.perm(ticket.resource):
                        word = \
                            tag.a(
                                '#%s' % ticket.id,
                                class_=ticket['status'],
                                href=req.href.ticket(int(ticket.id)),
                                title=shorten_line(ticket['summary'])
                            )
                except ResourceNotFound:
                    pass
               
                items.append(word)

        if items:
            return tag(items)
        else:
            return None
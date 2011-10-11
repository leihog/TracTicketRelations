# Created by Noah Kantrowitz on 2007-07-04.
# Copyright (c) 2007 Noah Kantrowitz. All rights reserved.
import re

from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.ticket.api import ITicketChangeListener, ITicketManipulator
from trac.util.compat import set, sorted
from trac.ticket.model import Ticket

from model import TicketLinks, extract_ticket_ids

class TicketRelationsSystem(Component):

    implements(IEnvironmentSetupParticipant, ITicketChangeListener, ITicketManipulator)
    
    NUMBERS_RE = re.compile(r'\d+', re.U)

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self.upgrade_environment(None)

    def environment_needs_upgrade(self, db):
        # Check for our custom fields
        if 'blocking' not in self.config['ticket-custom'] or 'blockedby' not in self.config['ticket-custom']:
            return True

        return False

    def upgrade_environment(self, db):
        custom = self.config['ticket-custom']
        config_dirty = False
        if 'blocking' not in custom:
            custom.set('blocking', 'text')
            custom.set('blocking.label', 'Blocking')
            config_dirty = True
        if 'blockedby' not in custom:
            custom.set('blockedby', 'text')
            custom.set('blockedby.label', 'Blocked By')
            config_dirty = True
        if config_dirty:
            self.config.save()
            
    # ITicketChangeListener methods
    def ticket_created(self, tkt):
        self.ticket_changed(tkt, '', tkt['reporter'], {})

    def ticket_changed(self, tkt, comment, author, old_values):
        db = self.env.get_db_cnx()

        links = TicketLinks(self.env, tkt, db)

        old_relations = {'blocking': set([]), 'blockedby': set([])}
        if "blocking" in old_values:
            old_relations['blocking'] = extract_ticket_ids(old_values['blocking'])

        if "blockedby" in old_values:
            old_relations['blockedby'] = extract_ticket_ids(old_values['blockedby'])

        links.save(old_relations, author, comment, tkt.time_changed, db)

        db.commit()

    def ticket_deleted(self, tkt):
        pass
        
    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        id = unicode(ticket.id)
        links = TicketLinks(self.env, ticket, db)
        links.blocking = extract_ticket_ids(ticket['blocking'] or '')
        links.blocked_by = extract_ticket_ids(ticket['blockedby'] or '')
        
        # Check that ticket does not have itself as a blocker 
        if id in links.blocking | links.blocked_by:
            yield 'blocked_by', 'This ticket is blocking itself'
            return

        # Check that there aren't any blocked_by in blocking or their parents
        blocking = links.blocking.copy()
        while len(blocking) > 0:
            if len(links.blocked_by & blocking) > 0:
                yield 'blocked_by', 'This ticket has circular dependencies'
                return
            new_blocking = set()
            for link in blocking:
                tmp_tkt = Ticket(self.env, link)
                new_blocking |= TicketLinks(self.env, tmp_tkt, db).blocking
            blocking = new_blocking
        
        for field in ('blocking', 'blockedby'):
            try:
                ids = self.NUMBERS_RE.findall(ticket[field] or '')
                for id in ids[:]:
                    cursor.execute('SELECT id FROM ticket WHERE id=%s', (id,))
                    row = cursor.fetchone()
                    if row is None:
                        ids.remove(id)
                ticket[field] = ', '.join(sorted(ids, key=lambda x: int(x)))
            except Exception, e:
                self.log.debug('TicketRelations: Error parsing %s "%s": %s', field, ticket[field], e)
                yield field, 'Not a valid list of ticket IDs'

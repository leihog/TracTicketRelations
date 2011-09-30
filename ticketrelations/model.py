# Created by Noah Kantrowitz on 2007-07-04.
# Copyright (c) 2007 Noah Kantrowitz. All rights reserved.
import re
from datetime import datetime

from trac.ticket.model import Ticket
from trac.util.compat import set, sorted
from trac.util.datefmt import utc, to_utimestamp

class TicketLinks(object):
    
    NUMBERS_RE = re.compile(r'\d+', re.U)

    def __init__(self, env, tkt, db=None):
        self.env = env
        if not isinstance(tkt, Ticket):
            tkt = Ticket(self.env, tkt)
        self.tkt = tkt

        db = db or self.env.get_db_cnx()
        cursor = db.cursor()

        self._old_blocking = set([])
        self._old_blocked_by = set([])

        cursor.execute("SELECT value FROM ticket_custom WHERE ticket=%s AND name='blocking' AND value != '' ORDER BY value", (self.tkt.id,))
        ids = self.NUMBERS_RE.findall((cursor.fetchone() or ('',))[0])
        self.blocking = set([int(num) for num, in ids])

        cursor.execute("SELECT value FROM ticket_custom WHERE ticket=%s AND name='blockedby' AND value != '' ORDER BY value", (self.tkt.id,))
        ids = self.NUMBERS_RE.findall((cursor.fetchone() or ('',))[0])
        self.blocked_by = set([int(num) for num, in ids])

    def save(self, author, comment='', when=None, db=None):
        """Save new links."""

        if when is None:
            when = datetime.now(utc)
        when_ts = to_utimestamp(when)
        
        handle_commit = False
        if db is None:
            db = self.env.get_db_cnx()
            handle_commit = True
        cursor = db.cursor()
        
        new_blocking = set(int(n) for n in self.blocking)
        new_blocked_by = set(int(n) for n in self.blocked_by)
        
        to_check = [
            # new, old, field
            (new_blocking, self._old_blocking, 'blockedby'),
            (new_blocked_by, self._old_blocked_by, 'blocking'),
        ]

        for new_ids, old_ids, field in to_check:
            for n in new_ids | old_ids:
                update_field = None
                if n in new_ids and n not in old_ids:
                    # New ticket added
                    update_field = lambda lst: lst.append(str(self.tkt.id))
                elif n not in new_ids and n in old_ids:
                    # Old ticket removed
                    update_field = lambda lst: lst.remove(str(self.tkt.id))
                
                if update_field is not None:
                    cursor.execute('SELECT value FROM ticket_custom WHERE ticket=%s AND name=%s', (n, str(field)))
                    old_value = (cursor.fetchone() or ('',))[0]
                    new_value = [x.strip() for x in old_value.split(',') if x.strip()]
                    update_field(new_value)
                    new_value = ', '.join(sorted(new_value, key=lambda x: int(x)))

                    cursor.execute('INSERT INTO ticket_change (ticket, time, author, field, oldvalue, newvalue) VALUES (%s, %s, %s, %s, %s, %s)', 
                                   (n, when_ts, author, field, old_value, new_value))

                    if comment:
                        cursor.execute('INSERT INTO ticket_change (ticket, time, author, field, oldvalue, newvalue) VALUES (%s, %s, %s, %s, %s, %s)', 
                                       (n, when_ts, author, 'comment', '', '(In #%s) %s'%(self.tkt.id, comment)))

                    cursor.execute('UPDATE ticket_custom SET value=%s WHERE ticket=%s AND name=%s', (new_value, n, field))
                    if not cursor.rowcount:
                        cursor.execute('INSERT INTO ticket_custom (ticket, name, value) VALUES (%s, %s, %s)', (n, field, new_value))

                    # refresh the changetime to prevent concurrent edits
                    cursor.execute('UPDATE ticket SET changetime=%s WHERE id=%s', (when_ts,n))

        if handle_commit:
            db.commit()

    def __nonzero__(self):
        return bool(self.blocking) or bool(self.blocked_by)
            
    def __repr__(self):
        def l(arr):
            arr2 = []
            for tkt in arr:
                arr2.append(str(tkt))
            return '[%s]'%','.join(arr2)
            
        return '<ticketrelations.model.TicketLinks #%s blocking=%s blocked_by=%s>'% \
               (self.tkt.id, l(getattr(self, 'blocking', [])), l(getattr(self, 'blocked_by', [])))
##TicketRelations

The TicketRelations plugin enables you to define dependency relations between tickets.

TicketRelations is based on **mastertickets by Noah Kantrowitz** but removes the extra fluff (graphs) that came with mastertickets. The original version is available from https://github.com/coderanger/trac-mastertickets

The concept is the same, in that you define ticket relations using the custom ticket fields "blocking" and "blocked by".

To enable TicketRelations, add the following to trac.ini: 

	[components]
	ticketrelations.* = enabled

	[ticket-custom]
	blocking = text
	blocking.label = Blocking
	blockedby = text
	blockedby.label = Blocked By

TicketRelations is made for and tested on Trac 0.12. I have no idea if it works on older versions.
The plugin is entirely safe to test and use as it will not interfere or alter existing data in any way.

##Flattr this project
[![Flattr this git repo](http://api.flattr.com/button/flattr-badge-large.png)](https://flattr.com/submit/auto?user_id=leihog&url=https://github.com/leihog/TracTicketRelations&title=TracTicketRelations&language=en_GB&tags=github&category=software) 

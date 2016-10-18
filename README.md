#AMC

Graduation project

# Robert Kreuzer

I did not get your email so I figure this is as good as any other method
to leave a small note for you.

As I mentioned this was my graduation project which was accompanied by a
seperate frontend project and a thesis. 

You'll find most of the techniques we talked about in this project.
There are custom decorators to aid testing and authentication. There are
generators and list/dictionary comprehensions. There is some subclassing
of Flask and the Marshmallow classes to add some functionality. Within the
models module you'll find some non basic SQLAlchemy techniques and raw
SQL statements.

THe most interesting parts to look at to see my coding style would be
the utils and models.meta modules. I believe it's all PEP8 complient :).

Looking back (almost half a year ago) I see that not all my ideals are
very well presented as I thought they were. My endpoints do contain some
logic that could(should) be extracted (especially a complicated query in
the `exercises` endpoint that is built based on various parameters.

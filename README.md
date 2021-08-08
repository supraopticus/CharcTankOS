# CharcTankOS

CharcTankOS is written in Python and used to control the function of a curing chamber for making charcuterie.  It reads and uploads data to Firebase so you will need to create a free account for that.  I intend to make an iOS app later so that I can view the data and change settings remotely.  I don't have any experience with android so that will not be on the agenda for me.

It is meant to run on a RaspberryPi and use the official 7in rPi touchscreen for a display.  The software is a work in progress and coding is a hobby for me so use at your own risk.  I understand that the layout of the code is a little messy.  I started to learn how to use classes in Python so you can tell which parts I wrote later on vs the earlier stuff.  Sorry for the mess, but it (mostly) works.

There are lines that need to be uncommented  / commented out depending on how you are controlling the TECs (peltiers). Just search for "MARK".  I'll try to come up with more detailed explanations as time goes on with the hope of doing a full write up of the project in the future.

For more details on the curing chamber construction, see my post on Reddit

https://www.reddit.com/r/Charcuterie/comments/orfh1o/my_fully_automated_custom_made_charctank_powered/?utm_source=share&utm_medium=ios_app&utm_name=iossmf

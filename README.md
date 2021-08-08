# CharcTankOS

CharcTankOS is written in Python and used to control the function of a curing chamber for making charcuterie.  It reads and uploads data to Firebase so you will need to create a free account for that.  I intend to make an iOS app later so that I can view the data and change settings remotely.  I don't have any experience with android so that will not be on the agenda for me.

It is meant to run on a RaspberryPi and use the official 7in rPi touchscreen for a display.  The software is a work in progress and coding is a hobby for me so use at your own risk.  I understand that the layout of the code is a little messy.  I started to learn how to use classes in Python so you can tell which parts I wrote later on vs the earlier stuff.  Sorry for the mess, but it (mostly) works.

There are lines that need to be uncommented  / commented out depending on how you are controlling the TECs (peltiers). Just search for "MARK".  I'll try to come up with more detailed explanations as time goes on with the hope of doing a full write up of the project in the future.

For more details on the curing chamber construction, see my post on Reddit

https://www.reddit.com/r/Charcuterie/comments/orfh1o/my_fully_automated_custom_made_charctank_powered/?utm_source=share&utm_medium=ios_app&utm_name=iossmf

Edit 8/8/2021: Added STL for TEC manifold.  I printed it out of PETG 20% infill.  I think it could be made out of PLA, but I didnt know at the time how much heat would be generated and didnt want to run into issues of warping.  To install this, you will need a 4in hole saw.  I designed all the printed parts in Fusion360 so I will include the links to those files in case anyone wants to make modifications. While the box that holds all the electronics is functional, some of the screw holes are slightly off so they will need to be modified if you're super OCD.  I'm able to hold each board down with one or two screws, so that was good enough for me.  Plus the electroics box takes over a day to print and since it takes up most of the bed, it's very prone to warping at the edges even with my enclosure.    

Parts list:

TEC Modules: https://www.aliexpress.com/item/32974339055.html?spm=a2g0s.9042311.0.0.2eb04c4dGorHiL

12v 30A Power Supply: https://www.amazon.com/gp/product/B01M03VPT6/ref=ppx_yo_dt_b_asin_title_o05_s00?ie=UTF8&psc=1

DHT22 Temp / Humidity Sensors: https://www.amazon.com/gp/product/B0795F19W6/ref=ppx_yo_dt_b_asin_title_o07_s00?ie=UTF8&psc=1

ElectroCookie Solderable Breadboard PCB Board (Mini): https://www.amazon.com/gp/product/B07ZV8FWM4/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1

Closed Cell Foam: https://www.amazon.com/gp/product/B07SZ5CMN3/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1

Parts if using ESC for controling TECs:

Hobbywing QuicRun 1060: https://www.amazon.com/gp/product/B01LZHBJ85/ref=ppx_yo_dt_b_asin_title_o09_s00?ie=UTF8&psc=1

Parts if building custom controller for TECs: 

ElectroCookie PCB Prototype Board Large Solderable Breadboard: https://www.amazon.com/gp/product/B082KY5Y5Z/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1

IRF3708 N-Channel Power MOSFET: https://www.amazon.com/gp/product/B088NJXWZT/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1

Wire Terminals: https://www.amazon.com/gp/product/B07QRHJ489/ref=ppx_yo_dt_b_asin_title_o04_s00?ie=UTF8&psc=1

High-Speed MOSFET Power Driver: https://www.amazon.com/gp/product/B08C7V67TY/ref=ppx_yo_dt_b_asin_title_o07_s00?ie=UTF8&psc=1

Assorted resistors (10k and some 220ohm should work): https://www.amazon.com/gp/product/B072BL2VX1/ref=ppx_yo_dt_b_asin_title_o04_s01?ie=UTF8&psc=1

Ceramic Capacitors: https://www.amazon.com/gp/product/B0899TVNYB/ref=ppx_yo_dt_b_asin_title_o04_s01?ie=UTF8&psc=1

Electrolytic Capacitors: https://www.amazon.com/gp/product/B07KC99W2K/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1

Some Headder Pins.  I had them laying around

Wire.  Pref 20 or 22 awg

Optional parts:

Long Jumper Wires: https://www.amazon.com/gp/product/B07GD2PGY4/ref=ppx_yo_dt_b_asin_title_o07_s00?ie=UTF8&psc=1

Long Flex Cable for rPi Touchscreen: https://www.amazon.com/gp/product/B00M4DAQH8/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1

EC3 Banana Plugs: https://www.amazon.com/gp/product/B07BHJH3NG/ref=ppx_yo_dt_b_asin_title_o08_s01?ie=UTF8&psc=1


3D printed parts (Fusion 360):

TEC Manifold: https://a360.co/2VxvnbH

Electronics Box: https://a360.co/3CqsbQ5

DHT22 Sensor Cover: I didn't make this so I'm just including the STL in the files.  Credit to SciMonster on Thingiverse.

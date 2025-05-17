## 📂 What's Included
Your download contains:
.
├── app.py               # Main application entry point
├── config.py            # Configuration (edit this first!)
├── models.py            # Database models
├── requirements.txt     # Python dependencies
├── static/
│   └── styles.css       # All CSS styles
└── templates/           # HTML templates
    ├── login.html       # Login page
    ├── dashboard.html   # Main interface
    └── ...              # Other template files

## 🔧 First-Time Setup
1. Create Tables in postgres SQL:
   -- role table (should be created first due to foreign key dependencies)
create table role (
    roleid serial primary key,
    rolename varchar(50) not null
);

-- admin/user table
create table admin (
    userid serial primary key,
    firstname varchar(100) not null,
    lastname varchar(100) not null,
    email varchar(255) not null unique,
    passwordhash varchar(255) not null,
    roleid int references role(roleid) not null
);

-- studyroom table
create table studyroom (
    roomid serial primary key,
    roomnumber varchar(20) not null unique,
    location varchar(100) not null,
    capacity int not null,
    isavailable boolean not null default true
);

-- asset table
create table asset (
    assetid serial primary key,
    name varchar(100) not null,
    type varchar(50) not null,
    isavailable boolean not null default true,
    description text
);

-- policy table
create table policy (
    policyid serial primary key,
    maxmodificationhours int not null,
    maxcancellationhours int not null
);

-- reservation table
create table reservation (
    reservationid serial primary key,
    userid int references admin(userid) not null,
    roomid int references studyroom(roomid) not null,
    starttime timestamp not null,
    endtime timestamp not null,
    status varchar(20) not null,
    check (endtime > starttime)
);

-- resetreservation table
create table resetreservation (
    resetreservationid serial primary key,
    assetid int references asset(assetid),
    userid int references admin(userid) not null,
    reserveddate timestamp not null,
    returndate timestamp not null,
    status varchar(20) not null,
    check (returndate > reserveddate)
);

-- maintenance table
create table maintenance (
    maintenanceid serial primary key,
    roomid int references studyroom(roomid) not null,
    startdate timestamp not null,
    enddate timestamp not null,
    reason text not null,
    check (enddate > startdate)
);

-- feedback table
create table feedback (
    feedbackid serial primary key,
    userid int references admin(userid) not null,
    roomid int references studyroom(roomid),
    assetid int references asset(assetid),
    rating int not null check (rating between 1 and 5),
    comment text,
    submittedat timestamp not null default current_timestamp,
    check (roomid is not null or assetid is not null)
);

-- adminlog table
create table adminlog (
    loginid serial primary key,
    adminid int references admin(userid) not null,
    action varchar(100) not null,
    timestamp timestamp not null default current_timestamp
);
   
   
2. Insert values into the table:
      
3. Edit config.py:
   - Set your secret key and username: 'SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/LibraryEase'
   

## Quick Start (You Already Downloaded the Files)

1. Navigate to project folder:
   cd path/to/LibraryEase

2. Install requirements:
   pip install -r requirements.txt

3. Run the application:
   Open app.py
   → Access at: http://localhost:5000


##  Help?

2. Missing dependencies?
   - Run: pip install -r requirements.txt --force-reinstall

3. Port already in use?
   - Try: flask run --port 5001


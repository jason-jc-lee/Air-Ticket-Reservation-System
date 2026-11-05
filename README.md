# Air-Ticket-Reservation-System
A full-stack flight booking application that utilizes a Flask and MySQL backend. Supports staff and customer roles to manage information.

## Application Rules
- Staff actions like creating flights and adding airplanes are checked against the database (i.e duplicate flights or invalid entries).
- Ticket purchases are blocked once a plane is full.
- Customers can only rate flights they’ve already taken.

## Features
- Customers: Can view flights, purchase tickets, view flight times/destinations/ratings. 
- Staff: Can manage flights, add airplanes, change flight status, and customers.

## Built With
Python (Flask), MySQL, HTML

## Database Design
![ER Diagram](ER%20Diagram.png)
![Relational Schema](Relational%20Schema.png)


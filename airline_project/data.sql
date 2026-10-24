


--creating tables
CREATE TABLE Airport (
    code CHAR(3) PRIMARY KEY, -- e.g. 'JFK'
    city VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('domestic', 'international', 'both'))
);
CREATE TABLE Airline (
    name VARCHAR(100) PRIMARY KEY
);

CREATE TABLE Airplane (
    airplane_id INT PRIMARY KEY,
    num_of_seats INT CHECK (num_of_seats > 0),
    manufacturer VARCHAR(50),
    age INT CHECK (age >= 0),
    airline_name VARCHAR(100),
    FOREIGN KEY (airline_name) REFERENCES Airline(name)
);

CREATE TABLE Airline_Staff (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(100) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    date_of_birth DATE,
    phone_number VARCHAR(20),
    airline_name VARCHAR(100),
    FOREIGN KEY (airline_name) REFERENCES Airline(name)
);

CREATE TABLE Customer (
    email VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    password VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    passport_number VARCHAR(20),
    passport_expiration DATE,
    passport_country VARCHAR(50),
    building_number VARCHAR(10),
    street VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50)
);

CREATE TABLE Flight (
    flight_number VARCHAR(10) PRIMARY KEY,
    departure_datetime DATETIME NOT NULL,
    arrival_datetime DATETIME NOT NULL,
    base_price DECIMAL(10,2) CHECK (base_price >= 0),
    status VARCHAR(20) 
        DEFAULT 'On Time'
        CHECK (status IN ('On Time', 'Delayed')),
    airplane_id INT,
    depart_airport_code CHAR(3),
    arrival_airport_code CHAR(3),
    airline_name VARCHAR(100),
    FOREIGN KEY (airplane_id) REFERENCES Airplane(airplane_id),
    FOREIGN KEY (depart_airport_code) REFERENCES Airport(code),
    FOREIGN KEY (arrival_airport_code) REFERENCES Airport(code),
    FOREIGN KEY (airline_name) REFERENCES Airline(name)
);

CREATE TABLE Ticket (
    ticket_id INT PRIMARY KEY,
    card_type VARCHAR(20)
        CHECK (card_type IN ('Credit', 'Debit')),
    card_number CHAR(16),
    name_on_card VARCHAR(100),
    expiration_date DATE,
    purchase_datetime DATETIME NOT NULL,
    customer_email VARCHAR(100),
    flight_number VARCHAR(10),
    FOREIGN KEY (customer_email) REFERENCES Customer(email),
    FOREIGN KEY (flight_number) REFERENCES Flight(flight_number)
);

--creating users

INSERT INTO Airline (name)
VALUES ('Jet Blue');


INSERT INTO Airport (code, city, country, type)
VALUES 
('JFK', 'New York', 'USA', 'international'),
('PVG', 'Shanghai', 'China', 'international');


INSERT INTO Customer (email, name, password, date_of_birth, phone_number)
VALUES
('somerandomperson@gmail.com', 'Random Person', 'person123', '1990-04-12', '555-1111'),
('johnathan.amazon@gmail.com', 'John Amazon', 'amazon123', '1985-09-21', '555-2222'),
('Hello.World@gmail.com', 'Hello World', 'world123', '1998-01-30', '555-3333');


INSERT INTO Airplane (airplane_id, num_of_seats, manufacturer, age, airline_name)
VALUES
(1001, 180, 'Airbus', 5, 'Jet Blue'),
(1002, 150, 'Boeing', 3, 'Jet Blue'),
(1003, 220, 'Airbus', 11, 'Jet Blue');



INSERT INTO Airline_Staff (username, password, first_name, last_name, email, date_of_birth, phone_number, airline_name)
VALUES
('SarahDoe123', 'sarahdoe', 'Sarah', 'Doe', 'sarah.doe@gmail.com', '1990-12-12', '555-1111', 'Jet Blue');


INSERT INTO Flight (
  flight_number, departure_datetime, arrival_datetime, base_price, status,
  airplane_id, depart_airport_code, arrival_airport_code, airline_name
)
VALUES
('JB101', '2025-11-15 08:00:00', '2025-11-16 10:00:00', 851.00, 'on-time', 1001, 'JFK', 'PVG', 'Jet Blue'),
('JB102', '2025-11-18 14:00:00', '2025-11-18 16:30:00', 904.00, 'delayed', 1002, 'PVG', 'JFK', 'Jet Blue'),
('JB103', '2025-12-01 09:30:00', '2025-12-02 11:00:00', 829.00, 'on-time', 1003, 'JFK', 'PVG', 'Jet Blue');

--part g
INSERT INTO Ticket (
  ticket_id, card_type, card_number, name_on_card, expiration_date,
  purchase_datetime, customer_email, flight_number
)
VALUES
(9001, 'Visa', '4111111111111111', 'Random Person', '2028-05-01', '2025-10-20 12:00:00', 'somerandomperson@gmail.com', 'JB101'),
(9002, 'MasterCard', '5500000000000004', 'Hello World', '2027-09-01', '2025-10-21 15:00:00', 'Hello.World@gmail.com', 'JB102'),
(9003, 'Visa', '340000000000009', 'Johnathan Amazon', '2029-01-01', '2025-10-22 18:30:00', 'johnathan.amazon@gmail.com', 'JB103'),
(9004, 'Visa', '4111111111111111', 'Random Person', '2028-05-01', '2025-10-25 10:00:00', 'somerandomperson@gmail.com', 'JB102');

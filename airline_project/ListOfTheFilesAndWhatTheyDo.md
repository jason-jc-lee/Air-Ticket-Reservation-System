airline_project/
├─ app.py | The Flask app that initializes the server and routes
├─ templates/
│  ├─ index.html | The home page for unregistered users                            
│  ├─ login_customer.html | Login page for customers   
│  ├─ login_staff.html |  Login page for staff    
│  ├─ search_results.html | Provides all available flights for customers
│  └─ purchase.html |  Allows viewing and option to buy the flight ticket
│  └─ purchase_confirm.html  |  The page where customers input their payment information for the flight
│  └─ staff_add_airplane.html  | The page where staff can add new airplanes and adjust their attributes
│  └─ staff_change_status.html | The page where staff can change the flight status
│  └─ register_customer.html | The page for unregistered users to become customers
│  └─ register_staff.html | The page for unregistered users to become staff 
│  └─ customer_home.html | The home page for customers, granting them their respective use cases
│  └─ staff_home.html | The home page for staff, granting them their respective use cases (i.e searching for all flights)
│  └─ rate_form.html  | Allows customers to rate and comment on previously taken flights
│  └─ staff_view_customers.html  | Allows staff to view customers of a flight
│  └─ view_ratings.html  | Allows staff to view ratings of a flight
│  └─ staff_reports.html  | Allows staff to view how much tickets were bought and money was made
├─ ListOfTheFilesAndWhatTheyDo.md | Our current file, allows us to look at what the files in airline_project does
└─ data.sql | Sample input data






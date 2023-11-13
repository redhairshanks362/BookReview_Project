# Litrate Book Review Hub

## Project Group A

This project aims to develop a RESTful API for a Book Review Platform using Flask. The platform will allow users to post book reviews, rate books, and comment on reviews. It will include user authentication, role-based access control, and advanced functionalities like search and filtering.

### Development

To run the website locally, you should clone the repository and install the Python modules from the requirements.txt file. After that, you need to define an environment variable named DATABASE_URL to point to your PostgreSQL database, and another environment variable named FLASK_APP with a value of application.py.

Finally, you can execute the following command to run the website on http://127.0.0.1:5000:$ flask run

### Usage

The website features a JWT authentication system that only allows access to logged-in users. Anyone can register a new Normal or Admin user by providing credentials and later log in with these credentials.

Once logged in, users are directed to the home page where they can search for a book to review by its title, author, or ISBN number. Filters such as Genre, Year, and Rating can also be added. The website then redirects users to the results page containing all the books that match the search.

Users can click on any book to access its details, including the title, author, year, and ISBN number. The website also uses the GoodReads API (www.goodreads.com) to display the number of reviews and the average rating that the book has received on GoodReads (if available). On the book detail page, users can view all the reviews and ratings that have been submitted for this book on the website. Users can also submit their own review for the book, including a rating between 1 and 5 and a textual review. A user is only allowed to review each book once.

### API

1. Home Page
   - Endpoint: /
   - Method: GET
   - Description: Renders the home page with a search bar for finding books.

2. User Registration
   - Endpoint: /registration
   - Methods: GET, POST
   - Description: Allows an unregistered user to register on the website with a unique username and password.

3. User Login
   - Endpoint: /login
   - Methods: GET, POST
   - Description: Allows a registered user to log in to the website with a username and password.

4. User Logout

   - Endpoint: /logout
   - Method: GET
   - Description: Logs out the user by popping the session variable and redirects to the login page.

5. Search Results

   - Endpoint: /results
   - Method: POST
   - Description: Displays a list of book results based on the user's search query and filters. 

6. Book Details

   - Endpoint: /books/<string:isbn>
   - Methods: GET, POST
   - Description: Displays details, existing reviews, and allows users to submit new reviews for a specific book identified by ISBN. Also includes comments functionality.

7. Edit Review

   - Endpoint: /reviews/<int:review_id>/edit
   - Methods: GET, POST
   - Description: Allows users to edit their own reviews.

8. Delete Review

   - Endpoint: /reviews/<int:review_id>/delete
   - Method: POST
   - Description: Allows users to delete their own reviews.

9. Edit Comment

   - Endpoint: /comments/<int:comment_id>/edit
   - Methods: GET, POST
   - Description: Allows users to edit their own comments.

10. Delete Comment

    - Endpoint: /comments/<int:comment_id>/delete
    - Method: POST
    - Description: Allows users to delete their own comments.

11. Add Book

    - Endpoint: /add_book
    - Methods: GET, POST
    - Description: Allows users to add a new book to the database. 

12. External API

    - Endpoint: /api/<string:isbn>
    - Method: GET
    - Description: Returns book details in JSON format for a specific ISBN. It also includes information from the Goodreads API if available.

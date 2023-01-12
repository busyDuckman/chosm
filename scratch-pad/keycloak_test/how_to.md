Looking for a thing to manage logins, because this simple task seems like a giant mess.

Key cloack seems to work, but there are a f' load of gotcha's:
  - use this to interface with python https://github.com/code-specialist/fastapi-keycloak
  - follow this https://fastapi-keycloak.code-specialist.com/quick_start/
  - But do this way https://stackoverflow.com/questions/65735580/why-does-keycloak-hide-the-service-account-admin-cli-user-under-users-sectio

  - you can get a link to the login page via http://127.0.0.1:8000/login-link
  - that also has a register link, but that does not work and tends to break web interface

  - the server does not start in pycharm with no reason provided. Use command line:


    cd scratch-pad/keycloak_test
    uvicorn test_keycloak:app

    - this looks useful https://stackoverflow.com/questions/69812281/how-to-save-the-keycloak-data-when-running-inside-docker-container

  - I followed the guides, managed to crash the registration screen, got full unrestricted access 
    to all the other users data. It's probably because IDK how to set this up, but it's not 
    great outa the box.
  - It feels like managing keycloak is a career, I need something more turnkey,  


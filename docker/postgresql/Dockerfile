# Use official PostgreSQL image as base image
FROM postgres:latest

# Set environment variables for the database name, username, and password
ENV POSTGRES_DB=music_appln
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=root

# Expose PostgreSQL default port
EXPOSE 5432

# Command to run PostgreSQL server
CMD ["postgres"]

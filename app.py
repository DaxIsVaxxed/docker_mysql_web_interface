import docker
from flask import Flask, render_template, request, redirect
import mysql.connector
import logging

app = Flask(__name__)
docker_client = docker.from_env()
logging.basicConfig(level=logging.DEBUG)

# MySQL Database Connection Configurations for the Two Containers
db_configs = {
    'mysql-container1': {
        'host': 'localhost',
        'user': 'root',
        'password': 'rootpassword',
        'database': 'mydatabase',
        'port': 3307
    },
    'mysql-container2': {
        'host': 'localhost',
        'user': 'root',
        'password': 'rootpassword',
        'database': 'mydatabase',
        'port': 3308
    }
}

# Track active container; initially set to mysql-container1
active_container_name = 'mysql-container1'

# Helper function to get MySQL connection
def get_db_connection(config):
    return mysql.connector.connect(**config)

# Fetch data from the active container
def fetch_container_data(config):
    try:
        connection = get_db_connection(config)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM data")
        data = cursor.fetchall()
        cursor.close()
        connection.close()
        return data
    except mysql.connector.Error as err:
        return []

@app.route('/')
def index():
    global active_container_name
    containers = {}
    data = {}

    # Loop through the container configs to get current container states
    for container_name, config in db_configs.items():
        try:
            container = docker_client.containers.get(container_name)
            container_status = container.status
            container_id = container.short_id
        except docker.errors.NotFound:
            container_status = "Stopped"
            container_id = "N/A"

        containers[container_name] = {'status': container_status, 'id': container_id}

        # Retrieve database data if the container is running
        if container_status == 'running':
            data[container_name] = fetch_container_data(config)

    # Render the index page with the container data
    return render_template('index.html', containers=containers, data=data, active_container=active_container_name)

# Route to add data to the active container
@app.route('/add_data', methods=['POST'])
def add_data():
    global active_container_name
    name = request.form['name']
    value = request.form['value']

    config = db_configs[active_container_name]
    try:
        connection = get_db_connection(config)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO data (name, value) VALUES (%s, %s)", (name, value))
        connection.commit()
        cursor.close()
        connection.close()
        app.logger.info(f"Data added to {active_container_name}.")
    except Exception as e:
        app.logger.error(f"Error adding data to {active_container_name}: {e}")

    return redirect('/')

# Route to delete data from the active container
@app.route('/delete_data', methods=['POST'])
def delete_data():
    global active_container_name

    config = db_configs[active_container_name]
    try:
        connection = get_db_connection(config)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM data")
        connection.commit()
        cursor.close()
        connection.close()
        app.logger.info(f"Data deleted from {active_container_name}.")
    except Exception as e:
        app.logger.error(f"Error deleting data from {active_container_name}: {e}")

    return redirect('/')

# Route to stop the active container and switch to the other container
@app.route('/stop_container', methods=['POST'])
def stop_container():
    global active_container_name
    try:
        # Stop the currently active container
        current_container = docker_client.containers.get(active_container_name)
        if current_container.status == 'running':
            try:
                current_container.stop()
                app.logger.info(f"{active_container_name} stopped successfully.")
            except docker.errors.APIError as e:
                app.logger.error(f"Failed to stop {active_container_name}: {e}")
                return redirect('/')

        # Switch to the other container
        active_container_name = 'mysql-container2' if active_container_name == 'mysql-container1' else 'mysql-container1'

        # Start the new active container
        new_container = docker_client.containers.get(active_container_name)
        if new_container.status != 'running':
            try:
                new_container.start()
                app.logger.info(f"{active_container_name} started successfully.")
            except docker.errors.APIError as e:
                app.logger.error(f"Failed to start {active_container_name}: {e}")
                return redirect('/')

    except docker.errors.NotFound as e:
        app.logger.error(f"Container not found: {e}")
    except Exception as e:
        app.logger.error(f"Unexpected error occurred while switching containers: {e}")

    return redirect('/')

if __name__ == '__main__':
    # Ensure only one container is running initially
    try:
        container1 = docker_client.containers.get('mysql-container1')
        container2 = docker_client.containers.get('mysql-container2')

        # Start container1 and stop container2 to ensure correct initial state
        if container1.status != 'running':
            container1.start()
            app.logger.info("mysql-container1 started successfully at app initialization.")
        if container2.status == 'running':
            container2.stop()
            app.logger.info("mysql-container2 stopped at app initialization.")

    except docker.errors.NotFound as e:
        app.logger.error(f"Container not found during initialization: {e}")
    except docker.errors.APIError as e:
        app.logger.error(f"API Error during initialization: {e}")
    except Exception as e:
        app.logger.error(f"Unexpected error during initial container setup: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)


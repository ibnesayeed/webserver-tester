# WebServer Tester

An HTTP testing and deployment system for CS 531 (Web Server Design) course projects.

## Test Locally

To test your server, run your server first, note down the host and port of the server (which can be on the local machine or on a remote machine), then execute the tester script against that `<host>` and `<port>`.

Currently, the testing script has an external dependency on NetCat (`nc`) utility for making requests. However, we plan to eliminate this dependency.

```
$ git clone https://github.com/ibnesayeed/webserver-tester.git
$ cd webserver-tester
$ pip install -r requirements.txt
$ ./tester.py -h

Usage:
./tester.py [[<host>]:[<port>] [<test-id>|<bucket-numbers>]]

<host>           : Hostname or IP address of the server to be tested (default: 'localhost')
<port>           : Port number of the server to be tested (default: '80')
<test-id>        : ID of an individual test function (e.g., 'test_1_healthy_server')
<bucket-numbers> : Comma separated list of bucket numbers (default: all buckets)
```

Alternatively, build a Docker image from the source to ensure all the dependencies are available and run tester script inside.

```
$ docker image build -t webserver-tester .
$ docker container run --rm -it webserver-tester ./tester.py -h
```

Be aware that the `localhost` inside of the container refers to the container itself and not the host machine, so use a host that is reachable from inside of the container.

Alternatively, the web interface can be used to test the server. The web interface can be deployed both on the host machine or in a Docker container. Here is how to run it in a container.

```
$ docker container run --rm -it -p 5000:5000 webserver-tester
```

Then access it from http://localhost:5000 and provide the `<host>:<port>` information in the appropriate form then run tests.

## Deploy and Test on Course's Test Machine

A machine is configured to build Docker images from students' private GitHub repositories that contain a `Dockerfile`. Go to http://cs531.cs.odu.edu/ and provide your CS ID in the appropriate form field then click "Deploy the Web Server" button. Depending on the network speed and complexity of the image, it might take some time to pull the source code and build an image. If an image is built successfully then it will automatically remove any existing containers of the corresponding student and deploy a new one. This newly deployed server will be accessible from `http://<cs-id>.cs531.cs.odu.edu/`.

**It is important that your `Dockerfile` is setup in a way that it runs the server on the network interface `0.0.0.0` and port `80` by default.**

Once your server is deployed, you can test it from the http://cs531.cs.odu.edu/ page using the appropriate form.

Alternatively, you can use command line to both deploy and test your server on the testing machine.

To deploy your instance:

```
$ curl -i http://cs531.cs.odu.edu/servers/<cs-id>
```

To run a specific test:

```
$ curl -i http://cs531.cs.odu.edu/tests/<host>:<port>/<test-id>
```

To run all tests in a bucket:

```
$ curl -i http://cs531.cs.odu.edu/tests/<host>:<port>/<bucket-number>
```

To run all tests:

```
$ curl -i http://cs531.cs.odu.edu/tests/<host>:<port>
```

gcloud auth application-default

sudo docker build -f client.Dockerfile -t turbiniactl/client:latest .
sudo docker run -ti \
    -v ~/.turbiniarc:/root/.turbiniarc \
    -v ~/.config/gcloud/application_default_credentials.json:/root/.config/gcloud/application_default_credentials.json \
    turbiniactl/client \
    turbiniactl status


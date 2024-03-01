export NEXUS_HOME=/root/nexus/nexus-data
docker run -d -p 8081:8081 \
  -p 28443:28443 \
  --name nexus \
  -u 0 \
  -v $NEXUS_HOME:/nexus-data \
  --restart unless-stopped \
  sonatype/nexus3:3.65.0

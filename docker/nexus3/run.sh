export NEXUS_HOME=/Users/gnyuan/Code/store/nexus
docker run -d -p 8081:8081 --name nexus -v $NEXUS_HOME:/nexus-data sonatype/nexus3:3.65.0

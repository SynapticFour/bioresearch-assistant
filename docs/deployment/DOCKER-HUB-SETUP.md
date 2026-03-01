# Docker Hub einrichten (optional)

Docker Hub ist **optional** — GitHub Container Registry (ghcr.io) funktioniert ohne Setup und ist für private Repos kostenlos.

Falls du zusätzlich zu ghcr.io auch auf Docker Hub pushen möchtest:

1. **Account anlegen:** https://hub.docker.com  
2. **Access Token erstellen:** Hub → Account Settings → Security → New Access Token  
3. **GitHub Secrets hinzufügen** (Repository → Settings → Secrets and variables → Actions):
   - `DOCKERHUB_USERNAME` = dein Docker-Hub-Benutzername  
   - `DOCKERHUB_TOKEN` = dein Access Token  
4. Ab dem nächsten manuellen **Build and Push Docker Images**-Lauf werden Images automatisch auf **beide** Registries (ghcr.io und Docker Hub) gepusht.

Images auf Docker Hub heißen dann z. B. `DEIN_USERNAME/bioresearch-backend:latest` und `DEIN_USERNAME/bioresearch-frontend:latest`.

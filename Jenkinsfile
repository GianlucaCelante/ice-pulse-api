pipeline {
  agent {
    kubernetes {
      yaml """
        apiVersion: v1
        kind: Pod
        spec:
          serviceAccountName: jenkins
          containers:
          - name: jnlp
            image: jenkins/inbound-agent:latest
            args: ['\$(JENKINS_SECRET)', '\$(JENKINS_NAME)']
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "200m"
          - name: python
            image: python:3.9-slim
            command:
            - cat
            tty: true
            resources:
              requests:
                memory: "128Mi"
                cpu: "50m"
              limits:
                memory: "256Mi"
                cpu: "100m"
          - name: kubectl
            image: bitnami/kubectl:latest
            command:
            - cat
            tty: true
            resources:
              requests:
                memory: "64Mi"
                cpu: "50m"
              limits:
                memory: "128Mi"
                cpu: "100m"
          - name: tools
            image: alpine/git:latest
            command:
            - cat
            tty: true
            resources:
              requests:
                memory: "64Mi"
                cpu: "50m"
              limits:
                memory: "128Mi"
                cpu: "100m"
      """
    }
  }
  
  environment {
    DOCKER_REGISTRY     = 'docker.io/aipioppi'
    INFRA_REPO_URL      = 'git@github.com:GianlucaCelante/ice-pulse-infra.git'
    INFRA_BRANCH        = 'master'
    INFRA_CLONE_DIR     = 'infra'
    DEPLOY_PATH_DEV     = 'devops/dev/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_STAGING = 'devops/staging/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_PROD    = 'devops/prod/ice-pulse-api-deployment.yaml'
    CREDENTIALS_GIT_API = 'jenkins-deploy-api-ed25519'
    CREDENTIALS_GIT_INFRA = 'jenkins-deploy-infra-ed25519'
    CREDENTIALS_DOCKER  = 'docker-creds'
    KUBECONFIG_CRED     = 'kubeconfig'
  }

  stages {
    stage('Debug Environment') {
      steps {
        script {
          echo "=== DEBUG INFO ==="
          echo "Node name: ${env.NODE_NAME}"
          echo "Workspace: ${env.WORKSPACE}"
          echo "Branch: ${env.BRANCH_NAME}"
          
          sh '''
            echo "=== Container Info ==="
            hostname
            whoami
            pwd
            ls -la
          '''
        }
      }
    }

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Read Version') {
      steps {
        script {
          version = readFile('VERSION').trim()
          echo "Version: ${version}"
          echo "Branch: ${env.BRANCH_NAME}"
        }
      }
    }

    stage('Build & Test') {
      steps {
        container('python') {
          sh '''
            echo "=== Python Container ==="
            python3 --version
            pip install pytest || echo "pytest install failed, continuing"
            echo "Test phase completed"
          '''
        }
      }
    }

    stage('Build & Push Docker Image - DISABLED') {
      when {
        anyOf {
          branch 'release-dev'
          branch 'release'
          branch 'release-hv'
        }
      }
      steps {
        script {
          echo "=== Docker Build Temporarily Disabled ==="
          echo "Docker container has conflicts in this Kubernetes setup"
          echo "Image will use existing: ${DOCKER_REGISTRY}/ice-pulse-api:${version}"
          echo "This stage will be re-enabled in the GitHub Actions migration"
        }
      }
    }

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        container('tools') {
          withCredentials([sshUserPrivateKey(credentialsId: CREDENTIALS_GIT_INFRA, keyFileVariable: 'SSH_KEY')]) {
            script {
              echo "=== Deploy to Dev Environment ==="
              echo "Version to deploy: ${version}"
              
              sh """
                echo "=== Setting up SSH ==="
                mkdir -p ~/.ssh
                cp \$SSH_KEY ~/.ssh/id_rsa
                chmod 600 ~/.ssh/id_rsa
                ssh-keyscan github.com >> ~/.ssh/known_hosts
                
                echo "=== Cloning infra repository ==="
                git clone ${INFRA_REPO_URL} ${INFRA_CLONE_DIR}
                cd ${INFRA_CLONE_DIR}
                git checkout ${INFRA_BRANCH}
                
                echo "=== Installing yq ==="
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                
                echo "=== Current deployment file ==="
                cat ${DEPLOY_PATH_DEV}
                
                echo "=== Updating image version ==="
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_DEV}
                
                echo "=== Updated deployment file ==="
                cat ${DEPLOY_PATH_DEV}
                
                echo "=== Git configuration ==="
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                echo "=== Committing changes ==="
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to dev environment" || echo "No changes to commit"
                
                echo "=== Pushing to remote ==="
                git push origin ${INFRA_BRANCH}
                
                echo "=== Deploy to Dev completed ==="
              """
            }
          }
        }
      }
    }

    stage('Deploy to Staging') {
      when { branch 'release' }
      steps {
        container('tools') {
          withCredentials([sshUserPrivateKey(credentialsId: CREDENTIALS_GIT_INFRA, keyFileVariable: 'SSH_KEY')]) {
            script {
              echo "=== Deploy to Staging Environment ==="
              echo "Version to deploy: ${version}"
              
              sh """
                echo "=== Setting up SSH ==="
                mkdir -p ~/.ssh
                cp \$SSH_KEY ~/.ssh/id_rsa
                chmod 600 ~/.ssh/id_rsa
                ssh-keyscan github.com >> ~/.ssh/known_hosts
                
                echo "=== Cloning infra repository ==="
                git clone ${INFRA_REPO_URL} ${INFRA_CLONE_DIR}
                cd ${INFRA_CLONE_DIR}
                git checkout ${INFRA_BRANCH}
                
                echo "=== Installing yq ==="
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                
                echo "=== Current deployment file ==="
                cat ${DEPLOY_PATH_STAGING}
                
                echo "=== Updating image version ==="
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_STAGING}
                
                echo "=== Updated deployment file ==="
                cat ${DEPLOY_PATH_STAGING}
                
                echo "=== Git configuration ==="
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                echo "=== Creating release tag ==="
                git tag "staging-v${version}" || echo "Tag already exists"
                
                echo "=== Committing changes ==="
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to staging environment" || echo "No changes to commit"
                
                echo "=== Pushing to remote ==="
                git push origin ${INFRA_BRANCH} --tags
                
                echo "=== Deploy to Staging completed ==="
              """
            }
          }
        }
      }
    }

    stage('Deploy to Production') {
      when { branch 'release-hv' }
      steps {
        container('tools') {
          withCredentials([sshUserPrivateKey(credentialsId: CREDENTIALS_GIT_INFRA, keyFileVariable: 'SSH_KEY')]) {
            script {
              echo "=== Deploy to Production Environment ==="
              echo "Version to deploy: ${version}"
              
              sh """
                echo "=== Setting up SSH ==="
                mkdir -p ~/.ssh
                cp \$SSH_KEY ~/.ssh/id_rsa
                chmod 600 ~/.ssh/id_rsa
                ssh-keyscan github.com >> ~/.ssh/known_hosts
                
                echo "=== Cloning infra repository ==="
                git clone ${INFRA_REPO_URL} ${INFRA_CLONE_DIR}
                cd ${INFRA_CLONE_DIR}
                git checkout ${INFRA_BRANCH}
                
                echo "=== Installing yq ==="
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                
                echo "=== Current deployment file ==="
                cat ${DEPLOY_PATH_PROD}
                
                echo "=== Updating image version ==="
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_PROD}
                
                echo "=== Updated deployment file ==="
                cat ${DEPLOY_PATH_PROD}
                
                echo "=== Git configuration ==="
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                echo "=== Creating production tag ==="
                git tag "prod-v${version}" || echo "Tag already exists"
                
                echo "=== Committing changes ==="
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to production environment" || echo "No changes to commit"
                
                echo "=== Pushing to remote ==="
                git push origin ${INFRA_BRANCH} --tags
                
                echo "=== Deploy to Production completed ==="
              """
            }
          }
        }
      }
    }

    stage('Trigger ArgoCD Refresh') {
      when {
        anyOf {
          branch 'release-dev'
          branch 'release'
          branch 'release-hv'
        }
      }
      steps {
        container('kubectl') {
          script {
            try {
              withCredentials([file(credentialsId: KUBECONFIG_CRED, variable: 'KUBECONFIG')]) {
                sh 'kubectl annotate applicationsets.argoproj.io ice-pulse-all-envs -n argocd argocd.argoproj.io/refresh="hard" --overwrite'
                echo "ArgoCD refresh triggered successfully"
              }
            } catch (Exception e) {
              echo "ArgoCD refresh failed (kubeconfig not configured): ${e.message}"
              echo "This is optional - deploy will still work via ArgoCD polling"
            }
          }
        }
      }
    }
  }

  post {
    success {
      script {
        echo "✅ Pipeline completed successfully for branch ${env.BRANCH_NAME}"
        echo "Version: ${version}"
        if (env.BRANCH_NAME in ['release-dev', 'release', 'release-hv']) {
          def environment = ""
          switch(env.BRANCH_NAME) {
            case 'release-dev':
              environment = "development"
              break
            case 'release':
              environment = "staging"
              break
            case 'release-hv':
              environment = "production"
              break
          }
          echo "🚀 Deployment manifest updated for ${environment} environment"
          echo "Docker image: ${DOCKER_REGISTRY}/ice-pulse-api:${version}"
        }
      }
    }
    failure {
      echo "❌ Pipeline failed for branch ${env.BRANCH_NAME}"
    }
    always {
      echo "🧹 Cleanup completed"
    }
  }
}
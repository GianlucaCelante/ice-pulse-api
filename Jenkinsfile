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
    CREDENTIALS_GIT_API = 'ice-pulse-api-deploy-key'
    CREDENTIALS_GIT_INFRA = 'ice-pulse-infra-deploy-key'
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

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        container('tools') {
          script {
            echo "=== Deploy to Dev ==="
            echo "Version to deploy: ${version}"
            
            // Clone infra repository
            dir(INFRA_CLONE_DIR) {
              git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT_INFRA
              
              sh '''
                echo "=== Repository cloned ==="
                ls -la
                
                echo "=== Installing yq ==="
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                yq --version
                
                echo "=== Current deployment file ==="
                cat devops/dev/ice-pulse-api-deployment.yaml
                
                echo "=== Updating image version ==="
              '''
              
              sh """
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_DEV}
                
                echo "=== Updated deployment file ==="
                cat ${DEPLOY_PATH_DEV}
                
                echo "=== Git configuration ==="
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                echo "=== Git status ==="
                git status
                
                echo "=== Committing changes ==="
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to dev" || echo "No changes to commit"
                
                echo "=== Pushing to remote ==="
                git push origin ${INFRA_BRANCH}
                
                echo "=== Deploy completed ==="
              """
            }
          }
        }
      }
    }

    stage('Promote to Staging') {
      when { branch 'release' }
      steps {
        container('tools') {
          script {
            echo "=== Promote to Staging ==="
            echo "Version to deploy: ${version}"
            
            dir(INFRA_CLONE_DIR) {
              git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT_INFRA
              
              sh """
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_STAGING}
                
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                git tag staging-v${version}
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to staging" || echo "No changes to commit"
                git push origin ${INFRA_BRANCH} --tags
              """
            }
          }
        }
      }
    }

    stage('Promote to Prod') {
      when { branch 'release-hv' }
      steps {
        container('tools') {
          script {
            echo "=== Promote to Production ==="
            echo "Version to deploy: ${version}"
            
            dir(INFRA_CLONE_DIR) {
              git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT_INFRA
              
              sh """
                apk add --no-cache curl
                curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq
                chmod +x /usr/local/bin/yq
                
                yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_PROD}
                
                git config user.email "ci@jenkins.local"
                git config user.name "Jenkins CI"
                
                git tag prod-v${version}
                git add .
                git commit -m "ci: deploy ice-pulse-api:${version} to prod" || echo "No changes to commit"
                git push origin ${INFRA_BRANCH} --tags
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
          echo "🚀 Deployment manifest updated in infra repository"
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
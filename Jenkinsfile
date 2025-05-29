pipeline {
  agent {
    kubernetes {
      label 'k8s-agent'
      yaml """
        apiVersion: v1
        kind: Pod
        metadata:
          labels:
            jenkins: k8s-agent
        spec:
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
            workingDir: /home/jenkins/agent
            resources:
              requests:
                memory: "128Mi"
                cpu: "50m"
              limits:
                memory: "256Mi"
                cpu: "100m"
          - name: docker
            image: docker:20.10-dind
            securityContext:
              privileged: true
            volumeMounts:
            - name: docker-sock
              mountPath: /var/run/docker.sock
            workingDir: /home/jenkins/agent
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "200m"
          - name: kubectl
            image: bitnami/kubectl:latest
            command:
            - cat
            tty: true
            workingDir: /home/jenkins/agent
            resources:
              requests:
                memory: "64Mi"
                cpu: "50m"
              limits:
                memory: "128Mi"
                cpu: "100m"
          volumes:
          - name: docker-sock
            hostPath:
              path: /var/run/docker.sock
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
    CREDENTIALS_GIT     = 'jenkins-deploy-api-ed25519'
    CREDENTIALS_DOCKER  = 'docker-creds'
    KUBECONFIG_CRED     = 'kubeconfig'
  }

  stages {
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
            pip install pytest
            pytest --maxfail=1 --disable-warnings -q
          '''
        }
      }
    }

    stage('Build & Push Image') {
      when {
        anyOf {
          branch 'release-dev'
          branch 'release'
          branch 'release-hv'
        }
      }
      steps {
        container('docker') {
          script {
            docker.withRegistry("https://index.docker.io/v1/", CREDENTIALS_DOCKER) {
              def img = docker.build("${DOCKER_REGISTRY}/ice-pulse-api:${version}")
              img.push()
            }
          }
        }
      }
    }

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        container('kubectl') {
          dir(INFRA_CLONE_DIR) {
            git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
            sh """
              # Installa yq se non presente
              which yq || (curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq)
              
              yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_DEV}
              git config user.email "ci@tuo-org.com"
              git config user.name "CI Bot"
              git add .
              git commit -m "ci: deploy ice-pulse-api:${version} to dev" || echo "No changes to commit"
              git push origin ${INFRA_BRANCH}
            """
          }
        }
      }
    }

    stage('Promote to Staging') {
      when { branch 'release' }
      steps {
        container('kubectl') {
          dir(INFRA_CLONE_DIR) {
            git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
            sh """
              which yq || (curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq)
              
              yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_STAGING}
              git tag staging-v${version}
              git config user.email "ci@tuo-org.com"
              git config user.name "CI Bot"
              git add .
              git commit -m "ci: deploy ice-pulse-api:${version} to staging" || echo "No changes to commit"
              git push origin ${INFRA_BRANCH} --tags
            """
          }
        }
      }
    }

    stage('Promote to Prod') {
      when { branch 'release-hv' }
      steps {
        container('kubectl') {
          dir(INFRA_CLONE_DIR) {
            git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
            sh """
              which yq || (curl -L https://github.com/mikefarah/yq/releases/download/v4.30.8/yq_linux_amd64 -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq)
              
              yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_PROD}
              git tag prod-v${version}
              git config user.email "ci@tuo-org.com"
              git config user.name "CI Bot"
              git add .
              git commit -m "ci: deploy ice-pulse-api:${version} to prod" || echo "No changes to commit"
              git push origin ${INFRA_BRANCH} --tags
            """
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
          withCredentials([file(credentialsId: KUBECONFIG_CRED, variable: 'KUBECONFIG')]) {
            sh 'kubectl annotate applicationsets.argoproj.io ice-pulse-all-envs -n argocd argocd.argoproj.io/refresh="hard" --overwrite'
          }
        }
      }
    }
  }

  post {
    success {
      echo "Pipeline completed for branch ${env.BRANCH_NAME}"
    }
    failure {
      mail to: 'gianluca.celante@gmail.com',
           subject: "Build failed: ${env.JOB_NAME} [${env.BUILD_NUMBER}]",
           body: "Pipeline fallita su branch ${env.BRANCH_NAME}. Controlla Jenkins."
    }
  }
}
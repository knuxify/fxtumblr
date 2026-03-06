group "default" {
  targets = ["fxtumblr", "fxtumblr-render"]
}

target "fxtumblr" {
  context = "."
  dockerfile = "docker/Dockerfile"
  target = "fxtumblr"
  tags = ["knuxify/fxtumblr:latest", "knuxify/fxtumblr:v2"]
}

target "fxtumblr-render" {
  context = "."
  dockerfile = "docker/Dockerfile"
  target = "fxtumblr-render"
  tags = ["knuxify/fxtumblr-render:latest", "knuxify/fxtumblr-render:v2"]
}

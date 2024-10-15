resource "aws_sqs_queue" "incoming_jobs_queue" {
  name                      = "incoming-jobs-queue.fifo"
  fifo_queue                = true
  max_message_size          = 10000
  message_retention_seconds = 86400
}

output "queue_url" {
  value = aws_sqs_queue.incoming_jobs_queue.url
}

data "aws_region" "current" {}

output "queue_region" {
  value = data.aws_region.current.id
}

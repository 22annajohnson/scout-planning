#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"

config_path = ARGV.fetch(0, ".github/yaml-validation.yml")
config = YAML.load_file(config_path)

includes = Array(config.fetch("include"))
excludes = Array(config.fetch("exclude", []))
rules = config.fetch("rules", {})

def matches_any?(path, patterns)
  patterns.any? { |pattern| File.fnmatch?(pattern, path, File::FNM_PATHNAME | File::FNM_EXTGLOB) }
end

def workflow_file?(path)
  path.start_with?(".github/workflows/")
end

def workflow_text_has_key?(content, key)
  content.match?(/^#{Regexp.escape(key)}:\s*($|[^#])/)
end

files = includes.flat_map { |pattern| Dir.glob(pattern) }
  .select { |path| File.file?(path) }
  .uniq
  .sort
  .reject { |path| matches_any?(path, excludes) }

errors = []

files.each do |path|
  parsed = nil

  if rules["require_valid_yaml"]
    begin
      parsed = YAML.load_file(path)
    rescue Psych::Exception => error
      errors << "#{path}: invalid YAML: #{error.message}"
      next
    end
  end

  next unless rules["validate_github_workflow_shape"] && workflow_file?(path)

  content = File.read(path)
  errors << "#{path}: missing top-level name" unless workflow_text_has_key?(content, "name")
  errors << "#{path}: missing top-level on" unless workflow_text_has_key?(content, "on")

  jobs = parsed.is_a?(Hash) ? parsed["jobs"] : nil
  unless jobs.is_a?(Hash) && jobs.any?
    errors << "#{path}: missing top-level jobs"
    next
  end

  jobs.each do |job_name, job|
    next if job.is_a?(Hash) && (job.key?("runs-on") || job.key?("uses"))

    errors << "#{path}: job #{job_name} must define runs-on or uses"
  end
end

if files.empty?
  warn "No YAML files matched #{config_path}"
  exit 1
end

if errors.any?
  warn errors.join("\n")
  exit 1
end

puts "Validated #{files.count} YAML files"

#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"

config_path = ARGV.fetch(0, ".github/markdown-validation.yml")
config = YAML.load_file(config_path)

includes = Array(config.fetch("include"))
excludes = Array(config.fetch("exclude", []))
rules = config.fetch("rules", {})

def matches_any?(path, patterns)
  patterns.any? { |pattern| File.fnmatch?(pattern, path, File::FNM_PATHNAME | File::FNM_EXTGLOB) }
end

files = includes.flat_map { |pattern| Dir.glob(pattern) }
  .select { |path| File.file?(path) }
  .uniq
  .sort
  .reject { |path| matches_any?(path, excludes) }

errors = []

files.each do |path|
  content = File.binread(path)

  if rules["require_utf8"] && !content.force_encoding("UTF-8").valid_encoding?
    errors << "#{path}: file is not valid UTF-8"
    next
  end

  lines = content.lines

  if rules["reject_conflict_markers"]
    lines.each_with_index do |line, index|
      next unless line.match?(/^(<<<<<<<|=======|>>>>>>>)($| )/)

      errors << "#{path}:#{index + 1}: unresolved merge conflict marker"
    end
  end

  next unless rules["require_balanced_fences"]

  fence = nil
  lines.each_with_index do |line, index|
    match = line.match(/^ {0,3}(`{3,}|~{3,})/)
    next unless match

    marker = match[1]
    marker_type = marker[0]
    marker_length = marker.length

    if fence.nil?
      fence = { type: marker_type, length: marker_length, line: index + 1 }
    elsif marker_type == fence[:type] && marker_length >= fence[:length]
      fence = nil
    end
  end

  if fence
    errors << "#{path}:#{fence[:line]}: unclosed fenced code block"
  end
end

if files.empty?
  warn "No Markdown files matched #{config_path}"
  exit 1
end

if errors.any?
  warn errors.join("\n")
  exit 1
end

puts "Validated #{files.count} Markdown files"

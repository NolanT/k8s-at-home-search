from typing import Optional
from pydantic import BaseModel

from info_model import InfoModel

# release_name, chart_name, repo_name, hajimari_icon, amount_lines, url, timestamp

class FluxHelmRelease(InfoModel):
  release_name: str
  chart_name: str
  repo_name: str
  hajimari_icon: Optional[str]
  amount_lines: int
  url: str
  timestamp: str

class FluxHelmReleaseScanner:
  api_version = "helm.toolkit.fluxcd.io"
  kind = "HelmRelease"
  def pre_check(self, stream) -> bool:
    try:
      contains_api_version = False
      contains_kind = False
      for line in stream:
        if line.strip().startswith("apiVersion: " + self.api_version):
          contains_api_version = True
        if line.strip() == "kind: " + self.kind:
          contains_kind = True
        if contains_api_version and contains_kind:
          return True
    except UnicodeDecodeError as e:
      print("unicode error", e) 
    return False

  def check(self, walk) -> bool:
    return walk('apiVersion', lambda x: x.startswith(self.api_version)) and \
      walk('kind', lambda x: x == self.kind) and \
      walk('spec.chart.spec.chart', lambda x: x is not None) and \
      walk('spec.chart.spec.sourceRef.kind', lambda x: x == "HelmRepository")

  def parse(self, walk, rest: InfoModel) -> FluxHelmRelease:
    chart_name = walk('spec.chart.spec.chart')
    release_name = walk('metadata.name')
    
    hajimari_icon = walk(
      'spec.values.ingress.main.annotations.hajimari\.io/icon',
      lambda x: x.strip()) or None
    return FluxHelmRelease.parse_obj(rest.dict() | {
      'chart_name': chart_name,
      'release_name': release_name,
      'hajimari_icon': hajimari_icon,
    })

  def create_table(self, c):
    c.execute('''DROP TABLE IF EXISTS flux_helm_release''')
    c.execute('''CREATE TABLE IF NOT EXISTS flux_helm_release
                  (release_name text NOT NULL, 
                  chart_name text NOT NULL, 
                  repo_name text NOT NULL, 
                  hajimari_icon text NULL, 
                  lines number NOT NULL,
                  url text NOT NULL, 
                  timestamp text NOT NULL)''')

  def insert(self, c, data: FluxHelmRelease):
    c.execute(
      "INSERT INTO flux_helm_release VALUES (?, ?, ?, ?, ?, ?, ?)", 
      (data.release_name, data.chart_name, data.repo_name, data.hajimari_icon, data.amount_lines, data.url, data.timestamp))
  
  def test(self, c) -> bool:
    c.execute("SELECT count(*) FROM flux_helm_release")
    return c.fetchone()[0] > 1600
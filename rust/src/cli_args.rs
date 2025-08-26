use clap::Parser;
use log::info;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub struct CommandLineArgs {
    #[arg(
        long,
        value_delimiter = ',',
        help = "Comma-separated list of Reddit post URLs"
    )]
    pub urls: Vec<String>,

    #[arg(
        long = "src-files",
        value_delimiter = ',',
        help = "Comma-separated list of file paths containing URLs"
    )]
    pub src_files: Vec<String>,

    #[arg(
        long,
        value_delimiter = ',',
        help = "Comma-separated list of subreddits (e.g., r/python,r/askreddit)"
    )]
    pub subs: Vec<String>,

    #[arg(
        long,
        value_delimiter = ',',
        help = "Comma-separated list of multireddits (e.g., m/programming)"
    )]
    pub multis: Vec<String>,
}

impl CommandLineArgs {
    pub fn parse_args() -> Self {
        let args = CommandLineArgs::parse();

        info!("Parsed {} URL(s) from --urls", args.urls.len());
        info!("Parsed {} file(s) from --src-files", args.src_files.len());
        info!("Parsed {} subreddit(s) from --subs", args.subs.len());
        info!("Parsed {} multireddit(s) from --multis", args.multis.len());

        args
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_command_line_args_default() {
        let args = CommandLineArgs {
            urls: vec![],
            src_files: vec![],
            subs: vec![],
            multis: vec![],
        };

        assert_eq!(args.urls.len(), 0);
        assert_eq!(args.src_files.len(), 0);
        assert_eq!(args.subs.len(), 0);
        assert_eq!(args.multis.len(), 0);
    }

    #[test]
    fn test_command_line_args_with_data() {
        let args = CommandLineArgs {
            urls: vec!["https://www.reddit.com/r/rust/comments/test/".to_string()],
            src_files: vec!["/tmp/urls.txt".to_string()],
            subs: vec!["r/rust".to_string(), "r/programming".to_string()],
            multis: vec!["m/programming".to_string()],
        };

        assert_eq!(args.urls.len(), 1);
        assert_eq!(args.src_files.len(), 1);
        assert_eq!(args.subs.len(), 2);
        assert_eq!(args.multis.len(), 1);

        assert_eq!(args.urls[0], "https://www.reddit.com/r/rust/comments/test/");
        assert_eq!(args.subs[0], "r/rust");
        assert_eq!(args.subs[1], "r/programming");
    }
}
